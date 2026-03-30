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
