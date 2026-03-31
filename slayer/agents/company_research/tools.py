"""Company research tools — @tool decorated for ReAct agent."""

from __future__ import annotations

import asyncio
import json

from langchain_core.tools import tool

from slayer.agents.company_research.sources import (
    CorpInfoSource,
    FinancialInfoSource,
    NaverNewsSource,
)


@tool
def search_news(company_name: str) -> str:
    """Search recent news articles about a company using Naver News API.

    Args:
        company_name: Company name to search (Korean preferred, e.g. '카카오')

    Returns:
        JSON string with news articles including title, description, link, pub_date.
    """
    source = NaverNewsSource()
    result = asyncio.run(source.fetch(company_name))
    return json.dumps(result, ensure_ascii=False, indent=2)


@tool
def get_corp_info(company_name: str) -> str:
    """Look up basic corporate information from the Korean Financial Services Commission API.

    Returns company name, CEO, employee count, industry, headquarters, founding date,
    and importantly the corp_reg_no (법인등록번호/crno) needed for financial data lookup.

    Args:
        company_name: Company name to search (Korean, e.g. '삼성전자')

    Returns:
        JSON string with corporate info. Use the 'corp_reg_no' field to call get_financial_info.
    """
    source = CorpInfoSource()
    result = asyncio.run(source.fetch(company_name))
    return json.dumps(result, ensure_ascii=False, indent=2)


@tool
def get_financial_info(company_name: str, crno: str) -> str:
    """Look up financial statements (revenue, profit, assets) from the Korean Financial Services Commission API.

    Requires the corp_reg_no (crno) from get_corp_info results.

    Args:
        company_name: Company name (for logging)
        crno: Corporate registration number (법인등록번호) from get_corp_info result

    Returns:
        JSON string with financial data: revenue, operating_profit, net_income, total_assets, debt_ratio, fiscal_year.
    """
    source = FinancialInfoSource()
    result = asyncio.run(source.fetch(company_name, crno=crno))
    return json.dumps(result, ensure_ascii=False, indent=2)


@tool
def validate_research_data(data_source: str, result_json: str) -> str:
    """Validate whether collected research data is complete and usable.

    Call after collecting data from a source to check quality.
    This is a deterministic check (no LLM call, no cost).

    Args:
        data_source: Source name ("corp_info", "financial_info", "news")
        result_json: Raw JSON string from the data collection tool

    Returns:
        JSON with is_valid, completeness_score (0-1), missing_fields, suggestions.
    """
    import json as _json
    try:
        data = _json.loads(result_json)
    except (ValueError, TypeError):
        return _json.dumps({"is_valid": False, "completeness_score": 0.0, "missing_fields": ["all"], "suggestions": "Invalid JSON. Retry the tool call."})

    if data_source == "corp_info":
        key_fields = ["corp_name", "ceo", "employee_count", "industry", "corp_reg_no"]
        present = [f for f in key_fields if data.get(f)]
        missing = [f for f in key_fields if not data.get(f)]
        score = len(present) / len(key_fields)
        return _json.dumps({"is_valid": score >= 0.4, "completeness_score": round(score, 2), "missing_fields": missing, "suggestions": "Proceed." if score >= 0.4 else "Data sparse. Try alternative name."})
    elif data_source == "financial_info":
        key_fields = ["revenue", "operating_profit", "net_income", "total_assets"]
        present = [f for f in key_fields if data.get(f)]
        missing = [f for f in key_fields if not data.get(f)]
        score = len(present) / len(key_fields) if key_fields else 0
        return _json.dumps({"is_valid": score >= 0.25, "completeness_score": round(score, 2), "missing_fields": missing, "suggestions": "Proceed." if score >= 0.25 else "Financial data unavailable. Skip."})
    elif data_source == "news":
        articles = data.get("articles", [])
        score = min(len(articles) / 5, 1.0)
        return _json.dumps({"is_valid": len(articles) > 0, "completeness_score": round(score, 2), "missing_fields": [] if articles else ["articles"], "suggestions": f"{len(articles)} articles." if articles else "No news. Proceed without."})
    else:
        return _json.dumps({"is_valid": bool(data), "completeness_score": 0.5, "missing_fields": [], "suggestions": "Unknown source."})
