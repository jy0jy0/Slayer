"""Gmail API 폴링 — 채용 관련 신규 메일 감지 및 상태 업데이트.

Flow:
    1. DB에서 users.gmail_last_history_id 조회
    2. Gmail History API로 신규 메일 delta 폴링
    3. 채용 관련 메일 필터링 (키워드 기반)
    4. classify_email() → GmailParseResult
    5. gmail_events INSERT + applications 상태 전이
    6. gmail_last_history_id 갱신

OAuth 토큰은 users 테이블에서 읽으며, 만료 시 자동 갱신.
"""

from __future__ import annotations

import base64
import logging
from datetime import datetime, timezone
from typing import Iterator

from slayer.pipelines.gmail_monitor.classifier import GmailParseError, classify_email
from slayer.schemas import GmailParseResult, GmailStatusType

logger = logging.getLogger(__name__)

# 채용 관련 메일 필터 키워드 (제목 기준)
_RECRUIT_KEYWORDS = [
    "합격", "불합격", "면접", "서류", "코딩테스트", "과제", "전형",
    "채용", "지원", "결과", "안내", "통보",
    "passed", "rejected", "interview", "screening", "offer",
    "application", "hiring", "recruit",
]


class GmailFetchError(Exception):
    """Gmail 폴링 중 발생하는 예외."""

    def __init__(self, stage: str, cause: Exception):
        self.stage = stage
        self.cause = cause
        super().__init__(f"Gmail fetch failed at {stage}: {cause}")


def poll_user(user_id: str) -> list[dict]:
    """단일 사용자의 신규 채용 메일을 폴링하고 처리.

    Args:
        user_id: users 테이블 UUID

    Returns:
        처리된 gmail_event 목록 (dict)

    Raises:
        GmailFetchError: Gmail API 또는 DB 오류
    """
    from slayer.db.session import is_db_available

    if not is_db_available():
        logger.warning("DB 없음 — Gmail 폴링 건너뜀")
        return []

    try:
        user = _get_user(user_id)
        if not user:
            logger.warning("User not found: %s", user_id)
            return []

        service = _build_gmail_service(user)
        messages = list(_fetch_new_messages(service, user))

        if not messages:
            logger.debug("신규 메일 없음: user=%s", user_id)
            return []

        processed = []
        for msg in messages:
            event = _process_message(service, msg, user_id)
            if event:
                processed.append(event)

        # history_id 갱신
        if messages:
            _update_history_id(user_id, service)

        logger.info("폴링 완료: user=%s, 처리=%d건", user_id, len(processed))
        return processed

    except GmailFetchError:
        raise
    except Exception as e:
        raise GmailFetchError(stage="poll_user", cause=e) from e


# ── 내부 함수 ─────────────────────────────────────────────────

def _get_user(user_id: str):
    """DB에서 사용자 조회."""
    import uuid
    from slayer.db.models import User
    from slayer.db.session import get_session

    with get_session() as session:
        return session.query(User).filter_by(id=uuid.UUID(user_id)).first()


def _build_gmail_service(user):
    """OAuth 토큰으로 Gmail API 서비스 빌드. 만료 시 자동 갱신."""
    from google.oauth2.credentials import Credentials
    from google.auth.transport.requests import Request
    from googleapiclient.discovery import build

    creds = Credentials(
        token=user.google_access_token,
        refresh_token=user.google_refresh_token,
        token_uri="https://oauth2.googleapis.com/token",
    )

    if creds.expired and creds.refresh_token:
        try:
            creds.refresh(Request())
            _save_refreshed_token(str(user.id), creds.token, creds.expiry)
        except Exception as e:
            logger.warning("토큰 갱신 실패: %s", e)

    return build("gmail", "v1", credentials=creds)


def _save_refreshed_token(user_id: str, new_token: str, expiry: datetime | None) -> None:
    """갱신된 access token을 DB에 저장."""
    import uuid
    from slayer.db.models import User
    from slayer.db.session import get_session

    try:
        with get_session() as session:
            user = session.query(User).filter_by(id=uuid.UUID(user_id)).first()
            if user:
                user.google_access_token = new_token
                if expiry:
                    user.token_expires_at = expiry
    except Exception as e:
        logger.warning("토큰 DB 저장 실패: %s", e)


def _fetch_new_messages(service, user) -> Iterator[dict]:
    """gmail_last_history_id 기준 신규 메일 목록 반환.

    history_id 없으면 최근 30일 메일로 초기화.
    """
    if user.gmail_last_history_id:
        try:
            yield from _fetch_by_history(service, user.gmail_last_history_id)
            return
        except Exception as e:
            logger.warning("History API 실패, 최근 메일로 fallback: %s", e)

    # 초기 폴링: 최근 7일 메일
    result = service.users().messages().list(
        userId="me",
        q="newer_than:7d",
        maxResults=50,
    ).execute()
    for msg in result.get("messages", []):
        yield msg


def _fetch_by_history(service, history_id: str) -> Iterator[dict]:
    """Gmail History API로 신규 메일 delta 조회."""
    result = service.users().history().list(
        userId="me",
        startHistoryId=history_id,
        historyTypes=["messageAdded"],
    ).execute()

    for history in result.get("history", []):
        for added in history.get("messagesAdded", []):
            yield added["message"]


def _process_message(service, msg: dict, user_id: str) -> dict | None:
    """단일 메일 처리: 채용 관련 여부 확인 → 분류 → DB 저장."""
    msg_id = msg["id"]

    # 중복 처리 방지
    if _is_already_processed(msg_id):
        return None

    # 메일 상세 조회
    try:
        detail = service.users().messages().get(
            userId="me", id=msg_id, format="full"
        ).execute()
    except Exception as e:
        logger.warning("메일 조회 실패 (id=%s): %s", msg_id, e)
        return None

    subject, sender, body, received_at = _parse_message(detail)

    # 채용 관련 키워드 필터
    if not _is_recruit_related(subject, body):
        return None

    # LLM 분류
    try:
        result = classify_email(
            subject=subject,
            body=body[:3000],  # 토큰 절약
            context_date=datetime.now(timezone.utc).isoformat(),
        )
    except GmailParseError as e:
        logger.warning("메일 분류 실패 (id=%s): %s", msg_id, e)
        return None

    # gmail_events INSERT + 상태 전이
    event_data = _save_event(
        user_id=user_id,
        msg_id=msg_id,
        subject=subject,
        sender=sender,
        received_at=received_at,
        snippet=detail.get("snippet", ""),
        result=result,
    )

    if result.status_type in (GmailStatusType.PASS, GmailStatusType.INTERVIEW):
        _handle_pass_or_interview(user_id, result, event_data)
    elif result.status_type in (GmailStatusType.FAIL, GmailStatusType.REJECT):
        _handle_rejection(user_id, result, event_data)

    return event_data


def _parse_message(detail: dict) -> tuple[str, str, str, datetime]:
    """메일 헤더와 본문 파싱."""
    headers = {h["name"]: h["value"] for h in detail["payload"]["headers"]}
    subject = headers.get("Subject", "")
    sender = headers.get("From", "")

    # 수신 시각
    internal_date = detail.get("internalDate")
    if internal_date:
        received_at = datetime.fromtimestamp(int(internal_date) / 1000, tz=timezone.utc)
    else:
        received_at = datetime.now(timezone.utc)

    body = _extract_body(detail["payload"])
    return subject, sender, body, received_at


def _extract_body(payload: dict) -> str:
    """Gmail payload에서 텍스트 본문 추출."""
    if payload.get("mimeType") == "text/plain":
        data = payload.get("body", {}).get("data", "")
        if data:
            return base64.urlsafe_b64decode(data).decode("utf-8", errors="ignore")

    for part in payload.get("parts", []):
        text = _extract_body(part)
        if text:
            return text

    return ""


def _is_recruit_related(subject: str, body: str) -> bool:
    """채용 관련 메일인지 키워드 기반으로 판단."""
    text = (subject + " " + body[:500]).lower()
    return any(kw in text for kw in _RECRUIT_KEYWORDS)


def _is_already_processed(msg_id: str) -> bool:
    """gmail_events 테이블에서 중복 확인."""
    try:
        from slayer.db.models import GmailEvent
        from slayer.db.session import get_session

        with get_session() as session:
            return session.query(GmailEvent).filter_by(
                gmail_message_id=msg_id
            ).first() is not None
    except Exception:
        return False


def _save_event(
    user_id: str,
    msg_id: str,
    subject: str,
    sender: str,
    received_at: datetime,
    snippet: str,
    result: GmailParseResult,
) -> dict:
    """gmail_events 테이블에 저장. 실패해도 dict 반환."""
    import uuid
    from slayer.db.models import GmailEvent
    from slayer.db.session import get_session, is_db_available

    event_data = {
        "gmail_message_id": msg_id,
        "subject": subject,
        "sender": sender,
        "received_at": received_at.isoformat(),
        "parsed_company": result.company,
        "parsed_status_type": result.status_type.value,
        "parsed_stage_name": result.stage_name,
        "raw_summary": result.raw_summary,
    }

    if not is_db_available():
        return event_data

    try:
        with get_session() as session:
            event = GmailEvent(
                id=uuid.uuid4(),
                user_id=uuid.UUID(user_id),
                gmail_message_id=msg_id,
                subject=subject,
                sender=sender,
                received_at=received_at,
                raw_snippet=snippet,
                parsed_company=result.company,
                parsed_status_type=result.status_type.value,
                parsed_stage_name=result.stage_name,
                parsed_next_step=result.next_step,
                raw_summary=result.raw_summary,
                process_status="processed",
            )
            if result.interview_details:
                det = result.interview_details
                event.interview_details = det.model_dump()
                if det.datetime_str:
                    try:
                        event.interview_datetime = datetime.fromisoformat(det.datetime_str)
                    except ValueError:
                        pass
            session.add(event)
            event_data["event_id"] = str(event.id)
    except Exception as e:
        logger.warning("gmail_events 저장 실패: %s", e)

    return event_data


def _handle_pass_or_interview(user_id: str, result: GmailParseResult, event_data: dict) -> None:
    """합격/면접 안내: applications 상태 → in_progress, 면접이면 Calendar 등록."""
    import uuid
    from slayer.db.models import Application, StatusHistory, Company
    from slayer.db.session import get_session, is_db_available

    if not is_db_available():
        return

    try:
        with get_session() as session:
            # 회사명으로 application 매칭
            company = session.query(Company).filter_by(name=result.company).first()
            if not company:
                logger.info("매칭 회사 없음: %s (수동 매칭 필요)", result.company)
                return

            app = (
                session.query(Application)
                .filter_by(user_id=uuid.UUID(user_id), company_id=company.id)
                .filter(Application.status.in_(["applied", "reviewing"]))
                .first()
            )
            if not app:
                return

            app.status = "in_progress"
            session.add(StatusHistory(
                id=uuid.uuid4(),
                user_id=uuid.UUID(user_id),
                application_id=app.id,
                previous_status="applied",
                new_status="in_progress",
                trigger_type="email_detected",
                triggered_by="gmail_monitor",
                evidence_summary=event_data.get("raw_summary"),
            ))

        # 면접 일정 Calendar 등록
        if result.status_type == GmailStatusType.INTERVIEW and result.interview_details:
            _create_interview_event(user_id, result, event_data)

    except Exception as e:
        logger.warning("상태 전이 실패: %s", e)


def _handle_rejection(user_id: str, result: GmailParseResult, event_data: dict) -> None:
    """불합격/거절: applications 상태 → rejected."""
    import uuid
    from slayer.db.models import Application, StatusHistory, Company
    from slayer.db.session import get_session, is_db_available

    if not is_db_available():
        return

    try:
        with get_session() as session:
            company = session.query(Company).filter_by(name=result.company).first()
            if not company:
                return

            app = (
                session.query(Application)
                .filter_by(user_id=uuid.UUID(user_id), company_id=company.id)
                .filter(Application.status.notin_(["rejected", "withdrawn", "final_pass"]))
                .first()
            )
            if not app:
                return

            prev_status = app.status
            app.status = "rejected"
            session.add(StatusHistory(
                id=uuid.uuid4(),
                user_id=uuid.UUID(user_id),
                application_id=app.id,
                previous_status=prev_status,
                new_status="rejected",
                trigger_type="email_detected",
                triggered_by="gmail_monitor",
                evidence_summary=event_data.get("raw_summary"),
            ))
    except Exception as e:
        logger.warning("거절 상태 전이 실패: %s", e)


def _create_interview_event(user_id: str, result: GmailParseResult, event_data: dict) -> None:
    """면접 일정 Calendar 이벤트 생성."""
    import uuid
    from slayer.db import repository

    det = result.interview_details
    if not det or not det.datetime_str:
        return

    try:
        start_dt = datetime.fromisoformat(det.datetime_str)
    except ValueError:
        return

    title = f"[면접] {result.company}" + (f" — {result.stage_name}" if result.stage_name else "")

    # Calendar API 연동 시도 (apply_pipeline과 동일 패턴)
    try:
        from slayer.pipelines.apply_pipeline.pipeline import _try_google_calendar
        google_event_id = _try_google_calendar(user_id, title, start_dt)
    except Exception:
        google_event_id = None

    repository.save_calendar_event(
        user_id=user_id,
        application_id=uuid.UUID(event_data["event_id"]) if "event_id" in event_data else uuid.uuid4(),
        event_type="interview",
        title=title,
        start_datetime=start_dt,
        google_event_id=google_event_id,
        sync_status="synced" if google_event_id else "pending",
    )


def _update_history_id(user_id: str, service) -> None:
    """users.gmail_last_history_id 갱신."""
    import uuid
    from slayer.db.models import User
    from slayer.db.session import get_session, is_db_available

    if not is_db_available():
        return

    try:
        profile = service.users().getProfile(userId="me").execute()
        new_history_id = profile.get("historyId")
        if new_history_id:
            with get_session() as session:
                user = session.query(User).filter_by(id=uuid.UUID(user_id)).first()
                if user:
                    user.gmail_last_history_id = new_history_id
                    user.gmail_last_poll_at = datetime.now(timezone.utc)
    except Exception as e:
        logger.warning("history_id 갱신 실패: %s", e)
