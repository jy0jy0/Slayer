"""DB repository — helper functions for saving entities.

All functions are fail-safe: if DB is not available, they log a warning and return None.
"""

from __future__ import annotations

import logging
import time
import uuid
from datetime import datetime
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
def save_company(research_output) -> Any:
    """Save or update company from CompanyResearchOutput."""
    from slayer.db.models import Company

    with get_session() as session:
        existing = session.query(Company).filter_by(name=research_output.company_name).first()

        data = {
            "name": research_output.company_name,
            "name_en": research_output.company_name_en,
            "summary": research_output.summary,
            "data_sources": research_output.data_sources,
            "researched_at": datetime.now(),
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
            for k, v in data.items():
                if v is not None and hasattr(existing, k):
                    setattr(existing, k, v)
            logger.info("Updated company: %s", research_output.company_name)
            return existing
        else:
            company = Company(id=uuid.uuid4(), **data)
            session.add(company)
            logger.info("Saved new company: %s", research_output.company_name)
            return company


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
def save_match_result(jd_json: str, resume_json: str, match_result) -> Any:
    """Save matching result. Stores JD, resume data, and ATS analysis."""
    import json as _json
    from slayer.db.models import Application, Company

    with get_session() as session:
        # Try to find company from JD data
        company_id = None
        try:
            jd_data = _json.loads(jd_json) if isinstance(jd_json, str) else jd_json
            company_name = jd_data.get("company", "")
            if company_name:
                company = session.query(Company).filter_by(name=company_name).first()
                if company:
                    company_id = company.id
        except Exception:
            pass

        app = Application(
            id=uuid.uuid4(),
            user_id=uuid.UUID('00000000-0000-0000-0000-000000000000'),  # still placeholder for user
            company_id=company_id or uuid.UUID('00000000-0000-0000-0000-000000000000'),
            status='reviewing',
            ats_score=match_result.ats_score,
            score_breakdown=match_result.score_breakdown,
            matched_keywords=match_result.matched_keywords,
            missing_keywords=match_result.missing_keywords,
            strengths=match_result.strengths,
            weaknesses=match_result.weaknesses,
            gap_summary=match_result.gap_summary,
        )
        session.add(app)
        logger.info("Saved match result: ATS %.0f", match_result.ats_score)
        return app


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
    from datetime import date, datetime, timedelta
    from slayer.db.models import JobPosting

    normalized = _normalize_url(url)
    with get_session() as session:
        cutoff = datetime.now() - timedelta(days=7)
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
def save_job_posting(jd_schema) -> Any:
    """Save parsed JD as a JobPosting row. Looks up company_id by name if available."""
    from slayer.db.models import Company, JobPosting

    with get_session() as session:
        company_id = None
        if jd_schema.company:
            company = session.query(Company).filter_by(name=jd_schema.company).first()
            if company:
                company_id = company.id

        overview = jd_schema.overview or {}
        deadline = None
        if hasattr(overview, "deadline"):
            deadline_str = overview.deadline
        else:
            deadline_str = overview.get("deadline") if isinstance(overview, dict) else None

        if deadline_str:
            from datetime import date
            import re
            m = re.search(r"(\d{4})[.\-/](\d{1,2})[.\-/](\d{1,2})", deadline_str)
            if m:
                try:
                    deadline = date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
                except ValueError:
                    pass

        posting = JobPosting(
            id=uuid.uuid4(),
            company_id=company_id,
            source_url=_normalize_url(jd_schema.url) if jd_schema.url else jd_schema.url,
            platform=jd_schema.platform,
            title=jd_schema.title,
            position=jd_schema.position,
            location=overview.location if hasattr(overview, "location") else (overview.get("location") if isinstance(overview, dict) else None),
            employment_type=overview.employment_type if hasattr(overview, "employment_type") else (overview.get("employment_type") if isinstance(overview, dict) else None),
            experience_level=overview.experience if hasattr(overview, "experience") else (overview.get("experience") if isinstance(overview, dict) else None),
            skills=jd_schema.skills,
            deadline=deadline,
            parsed_data=jd_schema.model_dump(),
        )
        session.add(posting)
        logger.info("Saved job posting: %s — %s", jd_schema.company, jd_schema.title)
        return posting
