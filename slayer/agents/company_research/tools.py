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
