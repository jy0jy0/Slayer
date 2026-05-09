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
# 주의: "안내", "결과", "지원", "서류", "과제", "application" 등 범용 단어는 제외
_RECRUIT_KEYWORDS = [
    # 한글 — 채용 전형에서만 쓰이는 표현
    "합격", "불합격", "면접", "코딩테스트", "전형",
    "채용", "서류전형", "입사", "지원서", "최종합격",
    # 영어 — 채용 특화
    "passed", "rejected", "interview", "screening",
    "job offer", "offer letter", "hiring", "recruit",
    "we'd like to invite", "congratulations on",
    "unfortunately", "move forward",
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
        for i, msg in enumerate(messages):
            if i > 0:
                import time
                time.sleep(2)  # Gemini free tier: 30 req/min → 2초 간격
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
        user = session.query(User).filter_by(id=uuid.UUID(user_id)).first()
        if user:
            session.expunge(user)  # 세션 닫혀도 속성 접근 가능하도록 분리
        return user


def _build_gmail_service(user):
    """OAuth 토큰으로 Gmail API 서비스 빌드. 만료 시 Supabase로 자동 갱신."""
    from google.oauth2.credentials import Credentials
    from googleapiclient.discovery import build

    access_token = user.google_access_token

    # 토큰 만료 시 Supabase refresh_token으로 자동 갱신
    if _is_token_expired(user) and user.supabase_refresh_token:
        fresh = _refresh_via_supabase(str(user.id), user.supabase_refresh_token)
        if fresh:
            access_token = fresh

    from slayer.config import GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET
    # google_refresh_token이 있으면 mid-run 만료 시 자동 갱신 가능
    creds = Credentials(
        token=access_token,
        refresh_token=user.google_refresh_token or None,
        token_uri="https://oauth2.googleapis.com/token",
        client_id=GOOGLE_CLIENT_ID or None,
        client_secret=GOOGLE_CLIENT_SECRET or None,
    )
    return build("gmail", "v1", credentials=creds)


def _is_token_expired(user) -> bool:
    """access token 만료 여부 확인 (5분 여유)."""
    from datetime import timezone, timedelta
    if not user.token_expires_at:
        return True
    now = datetime.now(timezone.utc)
    expires = user.token_expires_at
    if expires.tzinfo is None:
        expires = expires.replace(tzinfo=timezone.utc)
    return now >= expires - timedelta(minutes=5)


def _refresh_via_supabase(user_id: str, supabase_refresh_token: str) -> str | None:
    """Supabase refresh_token으로 새 Google access_token 자동 발급.

    Returns:
        새 provider_token(Google access_token), 실패 시 None
    """
    import urllib.request
    import json as _json
    from datetime import timezone, timedelta
    from slayer.config import SUPABASE_URL, SUPABASE_ANON_KEY

    url = f"{SUPABASE_URL}/auth/v1/token?grant_type=refresh_token"
    payload = _json.dumps({"refresh_token": supabase_refresh_token}).encode()
    req = urllib.request.Request(
        url,
        data=payload,
        headers={"apikey": SUPABASE_ANON_KEY, "Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = _json.loads(resp.read())

        new_provider_token   = data.get("provider_token", "")
        new_supabase_refresh = data.get("refresh_token", "") or supabase_refresh_token
        new_provider_refresh = data.get("provider_refresh_token", "")
        expires_in           = int(data.get("expires_in", 3600))

        if not new_provider_token:
            logger.warning("Supabase 갱신 응답에 provider_token 없음: %s", list(data.keys()))
            return None

        expiry = datetime.now(timezone.utc) + timedelta(seconds=expires_in)
        _save_refreshed_token(
            user_id, new_provider_token, expiry,
            supabase_refresh_token=new_supabase_refresh,
            provider_refresh_token=new_provider_refresh,
        )
        logger.info("Supabase 토큰 자동 갱신 완료: user=%s", user_id)
        return new_provider_token

    except Exception as e:
        logger.warning("Supabase 토큰 갱신 실패: %s", e)
        return None


def _save_refreshed_token(
    user_id: str,
    new_token: str,
    expiry: datetime | None,
    supabase_refresh_token: str = "",
    provider_refresh_token: str = "",
) -> None:
    """갱신된 토큰들을 DB에 저장."""
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
                if supabase_refresh_token:
                    user.supabase_refresh_token = supabase_refresh_token
                if provider_refresh_token:
                    user.google_refresh_token = provider_refresh_token
    except Exception as e:
        logger.warning("토큰 DB 저장 실패: %s", e)


def _fetch_new_messages(service, user) -> Iterator[dict]:
    """gmail_last_history_id 기준 신규 메일 목록 반환.

    history_id 없으면(첫 폴링) 최근 30일 메일 최대 200건을 가져온다.
    """
    if user.gmail_last_history_id:
        try:
            yield from _fetch_by_history(service, user.gmail_last_history_id)
            return
        except Exception as e:
            logger.warning("History API 실패, 최근 메일로 fallback: %s", e)

    # 초기 폴링: 최근 30일 메일
    result = service.users().messages().list(
        userId="me",
        q="newer_than:30d",
        maxResults=200,
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

    # 채용 프로세스 이메일이 아닌 경우 skip
    if result.company == "NOT_RECRUITMENT":
        logger.debug("채용 무관 메일 skip (id=%s): %s", msg_id, subject)
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


def _get_or_create_company(session, name: str):
    """회사명으로 Company를 찾거나 신규 생성."""
    import uuid as _uuid
    from slayer.db.models import Company

    company = session.query(Company).filter_by(name=name).first()
    if not company:
        company = Company(id=_uuid.uuid4(), name=name)
        session.add(company)
        session.flush()  # ID 확보 (세션 내에서 바로 참조 가능하도록)
        logger.info("이메일 감지로 신규 회사 등록: %s", name)
    return company


def _get_or_create_application(session, user_id: str, company, initial_status: str):
    """user + company 조합의 활성 Application을 찾거나 신규 생성.

    Returns:
        (application, created: bool)
    """
    import uuid as _uuid
    from slayer.db.models import Application

    app = (
        session.query(Application)
        .filter_by(user_id=_uuid.UUID(user_id), company_id=company.id)
        .filter(Application.status.notin_(["rejected", "withdrawn", "final_pass"]))
        .first()
    )
    if app:
        return app, False

    app = Application(
        id=_uuid.uuid4(),
        user_id=_uuid.UUID(user_id),
        company_id=company.id,
        status=initial_status,
    )
    session.add(app)
    session.flush()
    logger.info("이메일 감지로 신규 지원 건 생성: user=%s, company=%s, status=%s",
                user_id, company.name, initial_status)
    return app, True


def _handle_pass_or_interview(user_id: str, result: GmailParseResult, event_data: dict) -> None:
    """합격/면접 안내: applications 상태 → in_progress.

    지원 건이 없으면 'applied' 상태로 자동 생성 후 전이.
    면접이면 Calendar 등록도 수행.
    """
    import uuid
    from slayer.db.models import StatusHistory
    from slayer.db.session import get_session, is_db_available

    if not is_db_available():
        return

    try:
        with get_session() as session:
            company = _get_or_create_company(session, result.company)
            app, created = _get_or_create_application(
                session, user_id, company, initial_status="applied"
            )

            # 이미 최종 단계이면 전이 불필요
            if app.status in ("in_progress", "final_pass"):
                return

            prev_status = app.status
            app.status = "in_progress"

            if created:
                # 신규 생성: applied → in_progress 두 이력 기록
                session.add(StatusHistory(
                    id=uuid.uuid4(),
                    user_id=uuid.UUID(user_id),
                    application_id=app.id,
                    previous_status="scrapped",
                    new_status="applied",
                    trigger_type="email_detected",
                    triggered_by="gmail_monitor",
                    evidence_summary="이메일 감지로 자동 생성",
                ))

            session.add(StatusHistory(
                id=uuid.uuid4(),
                user_id=uuid.UUID(user_id),
                application_id=app.id,
                previous_status=prev_status,
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
    """불합격/거절: applications 상태 → rejected.

    지원 건이 없으면 'applied' 상태로 자동 생성 후 전이.
    """
    import uuid
    from slayer.db.models import StatusHistory
    from slayer.db.session import get_session, is_db_available

    if not is_db_available():
        return

    try:
        with get_session() as session:
            company = _get_or_create_company(session, result.company)
            app, created = _get_or_create_application(
                session, user_id, company, initial_status="applied"
            )

            if app.status in ("rejected", "withdrawn", "final_pass"):
                return

            prev_status = app.status

            if created:
                session.add(StatusHistory(
                    id=uuid.uuid4(),
                    user_id=uuid.UUID(user_id),
                    application_id=app.id,
                    previous_status="scrapped",
                    new_status="applied",
                    trigger_type="email_detected",
                    triggered_by="gmail_monitor",
                    evidence_summary="이메일 감지로 자동 생성",
                ))

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
