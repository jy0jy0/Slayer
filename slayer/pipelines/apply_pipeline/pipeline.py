"""지원 액션 파이프라인.

Flow:
    1. 기업 UPSERT (company_name으로 조회, 없으면 생성)
    2. applications INSERT + status_history 기록 (trigger: apply_action)
    3. Google Calendar 마감일 이벤트 등록 (deadline 있고 OAuth 토큰 있을 때)
    4. ApplyResponse 반환

입력: ApplyRequest
출력: ApplyResponse
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone

from slayer.db import repository
from slayer.schemas import ApplyRequest, ApplyResponse, CalendarEventResult

logger = logging.getLogger(__name__)


class ApplyError(Exception):
    """Apply Pipeline 실행 중 발생하는 예외."""

    def __init__(self, stage: str, cause: Exception):
        self.stage = stage
        self.cause = cause
        super().__init__(f"Apply pipeline failed at {stage}: {cause}")


def apply(req: ApplyRequest) -> ApplyResponse:
    """지원 액션 실행.

    DB 없이도 동작 (repository는 fail-safe). Calendar 연동은 선택적.

    Args:
        req: 지원 요청 (user_id, job_posting_id, resume_id, company_name 등)

    Returns:
        ApplyResponse: application_id, 생성된 calendar_events 포함

    Raises:
        ApplyError: 예상치 못한 오류
    """
    try:
        return _run(req)
    except ApplyError:
        raise
    except Exception as e:
        raise ApplyError(stage="apply", cause=e) from e


def _run(req: ApplyRequest) -> ApplyResponse:
    calendar_events: list[CalendarEventResult] = []

    # 1. 기업 UPSERT — UUID 반환
    company_id = repository.upsert_company_by_name(req.company_name)

    # 2. applications INSERT + status_history
    result = repository.save_application(req, company_id=company_id)
    if result:
        app_id, applied_at = result
        application_id = str(app_id)
        created_at = applied_at.isoformat()
    else:
        application_id = None
        created_at = datetime.now(timezone.utc).isoformat()

    # 3. Calendar 이벤트 (마감일)
    if req.deadline and application_id:
        cal_event = _create_deadline_event(req, application_id)
        if cal_event:
            calendar_events.append(cal_event)

    return ApplyResponse(
        success=True,
        application_id=application_id,
        calendar_events=calendar_events,
        created_at=created_at,
    )


def _create_deadline_event(req: ApplyRequest, application_id: str) -> CalendarEventResult | None:
    """마감일 Calendar 이벤트 생성.

    Google Calendar API 연동 가능 시 synced, 불가 시 pending으로 DB 저장.
    """
    import uuid
    from datetime import date

    try:
        deadline_date = date.fromisoformat(req.deadline)
    except (ValueError, TypeError):
        logger.warning("Invalid deadline format: %s", req.deadline)
        return None

    title = f"[지원 마감] {req.company_name} — {req.position}"
    start_dt = datetime(
        deadline_date.year, deadline_date.month, deadline_date.day,
        23, 59, 0, tzinfo=timezone.utc,
    )

    google_event_id = _try_google_calendar(req.user_id, title, start_dt)
    sync_status = "synced" if google_event_id else "pending"

    repository.save_calendar_event(
        user_id=req.user_id,
        application_id=uuid.UUID(application_id),
        event_type="deadline",
        title=title,
        start_datetime=start_dt,
        google_event_id=google_event_id,
        sync_status=sync_status,
    )

    return CalendarEventResult(
        event_type="deadline",
        google_event_id=google_event_id,
        title=title,
        start_datetime=start_dt.isoformat(),
        sync_status=sync_status,
    )


def _try_google_calendar(user_id: str, title: str, start_dt: datetime) -> str | None:
    """Google Calendar API로 이벤트 생성 시도.

    OAuth 토큰을 DB에서 조회하여 사용. 실패 시 None 반환 (에러 없음).
    """
    try:
        import uuid as _uuid
        from google.oauth2.credentials import Credentials
        from googleapiclient.discovery import build
        from slayer.db.models import User
        from slayer.db.session import get_session, is_db_available

        if not is_db_available():
            return None

        with get_session() as session:
            user = session.query(User).filter_by(id=_uuid.UUID(user_id)).first()
            if not user or not user.google_access_token:
                return None
            creds = Credentials(
                token=user.google_access_token,
                refresh_token=user.google_refresh_token,
                token_uri="https://oauth2.googleapis.com/token",
            )

        service = build("calendar", "v3", credentials=creds)
        event_body = {
            "summary": title,
            "start": {"dateTime": start_dt.isoformat(), "timeZone": "Asia/Seoul"},
            "end": {"dateTime": start_dt.isoformat(), "timeZone": "Asia/Seoul"},
        }
        result = service.events().insert(calendarId="primary", body=event_body).execute()
        return result.get("id")

    except Exception as e:
        logger.debug("Google Calendar API 연동 실패 (무시): %s", e)
        return None
