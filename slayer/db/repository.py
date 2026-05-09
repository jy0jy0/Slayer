"""DB repository — helper functions for saving entities.

All functions are fail-safe: if DB is not available, they log a warning and return None.
"""

from __future__ import annotations

import logging
import time
import uuid
from datetime import datetime, timezone
from typing import Any

from slayer.db.session import get_session, is_db_available

logger = logging.getLogger(__name__)


def _normalize_url(url: str) -> str:
    """쿼리 파라미터(트래킹 파라미터 등)를 제거한 정규화 URL 반환.

    JobKorea / Wanted 등 채용 사이트는 공고 식별자가 경로에 있고,
    rPageCode, logpath, airbridge_referrer 등 트래킹 파라미터는 캐시 키로 쓰면 안 됨.

    Examples:
        https://www.jobkorea.co.kr/Recruit/GI_Read/48980334?rPageCode=SL&logpath=21
        → https://www.jobkorea.co.kr/Recruit/GI_Read/48980334

        https://www.wanted.co.kr/wd/355759?airbridge_referrer=...
        → https://www.wanted.co.kr/wd/355759
    """
    from urllib.parse import urlparse, urlunparse
    parsed = urlparse(url)
    return urlunparse(parsed._replace(query="", fragment=""))


def _safe_db_op(func):
    """Decorator that catches DB errors and returns None."""
    def wrapper(*args, **kwargs):
        if not is_db_available():
            logger.debug("DB not available — skipping %s", func.__name__)
            return None
        try:
            return func(*args, **kwargs)
        except Exception as e:
            logger.warning("DB operation %s failed: %s", func.__name__, e)
            return None
    return wrapper


@_safe_db_op
def save_company(research_output) -> uuid.UUID | None:
    """Save or update company from CompanyResearchOutput. UUID 반환."""
    from slayer.db.models import Company

    with get_session() as session:
        existing = session.query(Company).filter_by(name=research_output.company_name).first()

        data = {
            "name": research_output.company_name,
            "name_en": research_output.company_name_en,
            "summary": research_output.summary,
            "data_sources": research_output.data_sources,
            "researched_at": datetime.now(timezone.utc),
        }

        if research_output.basic_info:
            bi = research_output.basic_info
            data.update({
                "industry": bi.industry,
                "ceo": bi.ceo,
                "founded_date": bi.founded_date,
                "employee_count": bi.employee_count,
                "headquarters": bi.headquarters,
                "crno": bi.corp_registration_number,
                "basic_info": bi.model_dump(),
            })

        if research_output.financial_info:
            data["financial_info"] = research_output.financial_info.model_dump()

        if research_output.recent_news:
            data["recent_news"] = [n.model_dump() for n in research_output.recent_news]

        if existing:
            company_id = existing.id
            for k, v in data.items():
                if v is not None and hasattr(existing, k):
                    setattr(existing, k, v)
            logger.info("Updated company: %s", research_output.company_name)
        else:
            company_id = uuid.uuid4()
            company = Company(id=company_id, **data)
            session.add(company)
            logger.info("Saved new company: %s", research_output.company_name)
    return company_id


@_safe_db_op
def save_agent_log(
    agent_name: str,
    status: str,
    input_summary: str = "",
    output_summary: str = "",
    tokens_used: int | None = None,
    duration_ms: int | None = None,
    error_message: str | None = None,
) -> Any:
    """Save agent execution log."""
    from slayer.db.models import AgentLog

    with get_session() as session:
        log = AgentLog(
            id=uuid.uuid4(),
            agent_name=agent_name,
            status=status,
            input_summary=input_summary[:500] if input_summary else "",
            output_summary=output_summary[:500] if output_summary else "",
            tokens_used=tokens_used,
            duration_ms=duration_ms,
            error_message=error_message,
        )
        session.add(log)
        logger.info("Saved agent log: %s (%s)", agent_name, status)
        return log


@_safe_db_op
def save_job_posting(jd_schema, source_url: str = "") -> uuid.UUID | None:
    """JD 파싱 결과를 job_postings 테이블에 저장. UUID 반환."""
    from datetime import date as _date
    from slayer.db.models import JobPosting

    job_id = uuid.uuid4()
    company_id = upsert_company_by_name(jd_schema.company) if jd_schema.company else None
    overview = getattr(jd_schema, "overview", None)

    deadline = None
    deadline_str = getattr(overview, "deadline", None)
    if deadline_str:
        try:
            deadline = _date.fromisoformat(deadline_str.replace(".", "-").replace("/", "-"))
        except (ValueError, TypeError):
            pass

    normalized_url = _normalize_url(source_url or getattr(jd_schema, "url", "") or "")

    with get_session() as session:
        job = JobPosting(
            id=job_id,
            company_id=company_id,
            source_url=normalized_url,
            platform=getattr(jd_schema, "platform", None),
            title=jd_schema.title or "",
            position=jd_schema.position or "",
            location=getattr(overview, "location", None),
            employment_type=getattr(overview, "employment_type", None),
            experience_level=getattr(overview, "experience", None),
            skills=getattr(jd_schema, "skills", None) or [],
            deadline=deadline,
            parsed_data=jd_schema.model_dump(),
        )
        session.add(job)
        logger.info("Saved job posting: %s @ %s", jd_schema.position, jd_schema.company)
    return job_id


@_safe_db_op
def save_match_result(
    match_result=None,
    resume_json: str | None = None,
    result=None,
    user_id: str | None = None,
    job_posting_id: uuid.UUID | None = None,
    resume_id: uuid.UUID | None = None,
    company_name: str | None = None,
) -> uuid.UUID | None:
    """매칭 결과를 applications 테이블에 draft(reviewing) 레코드로 저장. UUID 반환.

    Supports both the current API-style call:
        save_match_result(match_result, user_id=..., company_name=...)
    and the older Streamlit call:
        save_match_result(jd_json, resume_json, match_result)
    """
    from slayer.db.models import Application

    if result is not None:
        # Backward compatibility with the older Streamlit signature.
        match_result = result

    if not user_id:
        logger.warning("save_match_result skipped: user_id is required to satisfy DB foreign keys")
        return None

    user_uuid = uuid.UUID(user_id)
    if isinstance(job_posting_id, str):
        job_posting_id = uuid.UUID(job_posting_id)
    if isinstance(resume_id, str):
        resume_id = uuid.UUID(resume_id)

    company_id = None
    if company_name:
        company_id = upsert_company_by_name(company_name)
    if not company_id:
        logger.warning("save_match_result skipped: company_name/company_id is required")
        return None

    app_id = uuid.uuid4()
    with get_session() as session:
        app = Application(
            id=app_id,
            user_id=user_uuid,
            company_id=company_id,
            job_posting_id=job_posting_id,
            resume_id=resume_id,
            status="reviewing",
            ats_score=match_result.ats_score,
            score_breakdown=match_result.score_breakdown,
            matched_keywords=match_result.matched_keywords,
            missing_keywords=match_result.missing_keywords,
            strengths=match_result.strengths,
            weaknesses=match_result.weaknesses,
            gap_summary=match_result.gap_summary,
        )
        session.add(app)
        logger.info("Saved match result: ATS %.0f → application %s", match_result.ats_score, app_id)
    return app_id


@_safe_db_op
def get_cached_job_posting(url: str, position: str | None = None) -> Any:
    """URL(+ 선택적 직무명)으로 캐시된 JobPosting 조회.

    캐시 유효 조건:
    1. 7일 이내 파싱된 것
    2. deadline이 설정된 경우 → 아직 마감 전인 것
       (deadline이 지났으면 URL에 다른 공고가 올라왔을 수 있음)

    Args:
        url: 공고 URL
        position: 직무명 필터 (멀티-직무 공고에서 같은 URL·다른 직무 구분).
                  None이면 URL만으로 조회.
    """
    from datetime import date, timedelta
    from slayer.db.models import JobPosting

    normalized = _normalize_url(url)
    with get_session() as session:
        cutoff = datetime.now(timezone.utc) - timedelta(days=7)
        query = (
            session.query(JobPosting)
            .filter(JobPosting.source_url == normalized)
            .filter(JobPosting.created_at >= cutoff)
        )
        if position:
            query = query.filter(JobPosting.position == position)
        posting = query.order_by(JobPosting.created_at.desc()).first()
        if not posting:
            return None

        # deadline이 있고 이미 지났으면 캐시 무효
        if posting.deadline and posting.deadline < date.today():
            logger.info("캐시 무효 (마감됨): %s deadline=%s", posting.title, posting.deadline)
            return None

        logger.info("캐시 히트: %s (%s)", posting.title, normalized[:60])
        return posting


@_safe_db_op
def update_job_posting(url: str, fields: dict) -> Any:
    """URL 기준으로 JobPosting의 특정 필드를 업데이트.

    fields 예시:
        {
            "responsibilities": [...],
            "requirements": {"required": [...], "preferred": [...]},
            "skills": [...],
            "benefits": [...],
            "process": [...],
        }
    parsed_data JSONB도 동일하게 업데이트됨.
    """
    from slayer.db.models import JobPosting

    normalized = _normalize_url(url)
    with get_session() as session:
        posting = (
            session.query(JobPosting)
            .filter(JobPosting.source_url == normalized)
            .order_by(JobPosting.created_at.desc())
            .first()
        )
        if not posting:
            logger.warning("update_job_posting: URL에 해당하는 공고 없음 — %s", normalized)
            return None

        # parsed_data JSONB 업데이트 (기존 데이터 유지하면서 덮어쓰기)
        import copy
        parsed = copy.deepcopy(posting.parsed_data or {})
        parsed.update(fields)
        posting.parsed_data = parsed

        # 컬럼 직접 업데이트
        if "skills" in fields:
            posting.skills = fields["skills"]

        from sqlalchemy.orm.attributes import flag_modified
        flag_modified(posting, "parsed_data")

        logger.info("Updated job posting fields %s: %s", list(fields.keys()), url[:60])
        return posting


@_safe_db_op
def update_application_fields(application_id: uuid.UUID, **fields) -> bool:
    """Application 레코드의 특정 필드를 업데이트. 성공 시 True."""
    if not is_db_available():
        return False
    try:
        from slayer.db.models import Application
        with get_session() as session:
            app = session.query(Application).filter_by(id=application_id).first()
            if not app:
                logger.warning("update_application_fields: application %s not found", application_id)
                return False
            for k, v in fields.items():
                if hasattr(app, k):
                    setattr(app, k, v)
            logger.info("Updated application %s: %s", application_id, list(fields.keys()))
        return True
    except Exception as e:
        logger.warning("update_application_fields failed: %s", e)
        return False


@_safe_db_op
def save_parsed_resume(
    user_id: str,
    file_name: str,
    file_type: str,
    file_url: str,
    parsed_resume,
) -> uuid.UUID | None:
    """이력서 파싱 결과를 resumes 테이블에 저장. resume UUID 반환."""
    from slayer.db.models import Resume

    resume_id = uuid.uuid4()
    with get_session() as session:
        resume = Resume(
            id=resume_id,
            user_id=uuid.UUID(user_id),
            file_name=file_name,
            file_type=file_type,
            source_format=parsed_resume.source_format,
            file_url=file_url,
            parse_status="completed",
            parsed_data=parsed_resume.model_dump(),
        )
        session.add(resume)
        logger.info("Saved parsed resume: %s", file_name)
    return resume_id


def save_application(req, company_id: uuid.UUID | None, application_id: uuid.UUID | None = None) -> tuple[uuid.UUID, datetime] | None:
    """applications 테이블에 지원 건 INSERT + status_history 기록.

    Returns:
        (application_id, applied_at) 튜플. DB 없으면 None.
    """
    if not is_db_available():
        logger.debug("DB not available — skipping save_application")
        return None
    try:
        from datetime import date as _date
        from slayer.db.models import Application, StatusHistory

        app_id = application_id or uuid.uuid4()
        now = datetime.now(timezone.utc)
        _placeholder = uuid.UUID('00000000-0000-0000-0000-000000000000')

        with get_session() as session:
            app = Application(
                id=app_id,
                user_id=uuid.UUID(req.user_id),
                company_id=company_id or _placeholder,
                job_posting_id=uuid.UUID(req.job_posting_id) if req.job_posting_id else None,
                resume_id=uuid.UUID(req.resume_id) if req.resume_id else None,
                status="applied",
                ats_score=req.ats_score,
                matched_keywords=req.matched_keywords or [],
                missing_keywords=req.missing_keywords or [],
                gap_summary=req.gap_summary,
                optimized_resume_url=req.optimized_resume_url,
                cover_letter_text=req.cover_letter,
                applied_at=now,
                deadline=_date.fromisoformat(req.deadline) if req.deadline else None,
            )
            session.add(app)
            session.add(StatusHistory(
                id=uuid.uuid4(),
                user_id=uuid.UUID(req.user_id),
                application_id=app_id,
                previous_status="reviewing",
                new_status="applied",
                trigger_type="apply_action",
                triggered_by="apply_pipeline",
            ))
            logger.info("Saved application: %s @ %s", req.position, req.company_name)
            return app_id, now
    except Exception as e:
        logger.warning("DB operation save_application failed: %s", e)
        return None


@_safe_db_op
def upsert_company_by_name(company_name: str) -> uuid.UUID | None:
    """company_name으로 기업 조회, 없으면 최소 정보로 INSERT. UUID 반환."""
    from slayer.db.models import Company

    with get_session() as session:
        existing = session.query(Company).filter_by(name=company_name).first()
        if existing:
            return existing.id
        company_id = uuid.uuid4()
        session.add(Company(id=company_id, name=company_name))
        logger.info("Created company placeholder: %s", company_name)
        return company_id


@_safe_db_op
def save_calendar_event(
    user_id: str,
    application_id: uuid.UUID,
    event_type: str,
    title: str,
    start_datetime: datetime,
    end_datetime: datetime | None = None,
    description: str | None = None,
    location: str | None = None,
    gmail_event_id: uuid.UUID | None = None,
    google_event_id: str | None = None,
    sync_status: str = "pending",
) -> Any:
    """calendar_events 테이블에 일정 저장."""
    from slayer.db.models import CalendarEvent

    with get_session() as session:
        event = CalendarEvent(
            id=uuid.uuid4(),
            user_id=uuid.UUID(user_id),
            application_id=application_id,
            gmail_event_id=gmail_event_id,
            google_event_id=google_event_id,
            event_type=event_type,
            title=title,
            description=description,
            start_datetime=start_datetime,
            end_datetime=end_datetime,
            location=location,
            sync_status=sync_status,
        )
        session.add(event)
        logger.info("Saved calendar event: %s (%s)", title, event_type)
        return event
