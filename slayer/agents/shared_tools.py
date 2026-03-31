"""Shared tools available to multiple agents."""
from __future__ import annotations

import json
import logging

from langchain_core.tools import tool

logger = logging.getLogger(__name__)


@tool
def get_cached_company_research(company_name: str) -> str:
    """Check DB cache for existing company research (< 7 days old).

    Args:
        company_name: The company name to look up

    Returns:
        JSON with found status, cached data if available, and suggestion.
    """
    from datetime import datetime

    try:
        from slayer.db.session import get_session, is_db_available

        if not is_db_available():
            return json.dumps(
                {"found": False, "data": None, "age_days": None, "suggestion": "research_needed"}
            )

        from slayer.db.models import Company

        with get_session() as session:
            company = session.query(Company).filter_by(name=company_name).first()
            if company and company.researched_at:
                now = datetime.now(company.researched_at.tzinfo) if company.researched_at.tzinfo else datetime.now()
                age_days = (now - company.researched_at).days
                if age_days <= 7:
                    data = {
                        "company_name": company.name,
                        "summary": company.summary,
                        "basic_info": company.basic_info,
                        "financial_info": company.financial_info,
                        "recent_news": company.recent_news,
                    }
                    return json.dumps(
                        {"found": True, "data": data, "age_days": age_days, "suggestion": "use_cached"},
                        ensure_ascii=False,
                    )
                return json.dumps(
                    {"found": True, "data": None, "age_days": age_days, "suggestion": "research_needed"}
                )
            return json.dumps(
                {"found": False, "data": None, "age_days": None, "suggestion": "research_needed"}
            )
    except Exception as e:
        logger.warning("Cache lookup failed: %s", e)
        return json.dumps(
            {"found": False, "data": None, "age_days": None, "suggestion": "research_needed"}
        )


@tool
def validate_json_output(json_str: str, expected_schema_name: str) -> str:
    """Validate JSON against expected schema.

    Supported schemas: match_result, company_research, cover_letter, resume_block.

    Args:
        json_str: The JSON string to validate
        expected_schema_name: Name of the expected schema

    Returns:
        JSON with is_valid (bool), errors list, and warnings list.
    """
    SCHEMAS = {
        "match_result": {
            "required": ["ats_score"],
            "optional": [
                "score_breakdown",
                "matched_keywords",
                "missing_keywords",
                "strengths",
                "weaknesses",
                "gap_summary",
            ],
        },
        "company_research": {
            "required": ["company_name"],
            "optional": [
                "company_name_en",
                "basic_info",
                "financial_info",
                "recent_news",
                "summary",
            ],
        },
        "cover_letter": {
            "required": ["cover_letter"],
            "optional": ["key_points", "jd_keyword_coverage", "word_count"],
        },
        "resume_block": {
            "required": ["block_type", "order", "content"],
            "optional": ["relevance_score"],
        },
    }

    try:
        data = json.loads(json_str)
        if not isinstance(data, dict):
            return json.dumps({"is_valid": False, "errors": ["JSON output must be an object, not array or primitive"], "warnings": []})
    except (json.JSONDecodeError, TypeError) as e:
        return json.dumps({"is_valid": False, "errors": [f"Invalid JSON: {e}"], "warnings": []})

    schema = SCHEMAS.get(expected_schema_name)
    if not schema:
        return json.dumps(
            {"is_valid": False, "errors": [f"Unknown schema: {expected_schema_name}"], "warnings": []}
        )

    errors = [
        f"Missing required: {f}" for f in schema["required"] if f not in data or data[f] is None
    ]
    warnings = [f"Optional missing: {f}" for f in schema["optional"] if f not in data]

    return json.dumps({"is_valid": len(errors) == 0, "errors": errors, "warnings": warnings})
