"""Company research orchestrator.

Owner: Jiho
Migration: moved from feat/company-research branch.
"""

from __future__ import annotations

import asyncio
import json
import logging
import re
from datetime import datetime
from pathlib import Path

from slayer.agents.company_research.llm_client import synthesize_research
from slayer.agents.company_research.sources import (
    CorpInfoSource,
    FinancialInfoSource,
    NaverNewsSource,
)
from slayer.schemas import (
    BasicInfo,
    CompanyResearchOutput,
    FinancialInfo,
    NewsItem,
)

logger = logging.getLogger(__name__)

OUTPUT_DIR = Path("research_output")


def _safe_filename(name: str) -> str:
    return re.sub(r'[\\/:*?"<>|]', "_", name)


async def _collect_data(company_name: str) -> dict:
    """Collect data concurrently from the three sources."""
    news_source = NaverNewsSource()
    corp_source = CorpInfoSource()
    financial_source = FinancialInfoSource()

    news_task = asyncio.create_task(news_source.fetch(company_name))
    corp_task = asyncio.create_task(corp_source.fetch(company_name))

    news_data, corp_data = await asyncio.gather(news_task, corp_task)

    # Financial lookup requires the corp registration number, so run after corp_info.
    crno = corp_data.get("corp_reg_no", "")
    financial_data: dict = {}
    if crno:
        financial_data = await financial_source.fetch(company_name, crno=crno)

    return {
        "naver_news": news_data,
        "corp_info": corp_data,
        "financial_info": financial_data,
    }


def _save_result(
    company_name: str, result: dict, output_path: str | None = None
) -> str:
    """Persist the result to a JSON file."""
    if output_path:
        path = Path(output_path)
    else:
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{_safe_filename(company_name)}_{timestamp}.json"
        path = OUTPUT_DIR / filename

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return str(path)


def _dict_to_schema(result: dict) -> CompanyResearchOutput:
    """Convert the LLM synthesis result dict into a CompanyResearchOutput schema."""
    bi = result.get("basic_info") or {}
    fi = result.get("financial_info")
    news_raw = result.get("recent_news") or []

    return CompanyResearchOutput(
        company_name=result.get("company_name", ""),
        company_name_en=result.get("company_name_en"),
        basic_info=BasicInfo(**{k: bi.get(k) for k in BasicInfo.model_fields}),
        financial_info=(
            FinancialInfo(
                **{k: (fi or {}).get(k) for k in FinancialInfo.model_fields}
            )
            if fi
            else None
        ),
        recent_news=[
            NewsItem(**{k: n.get(k) for k in NewsItem.model_fields})
            for n in news_raw
        ],
        summary=result.get("summary", ""),
        data_sources=result.get("data_sources", []),
        researched_at=result.get("researched_at", datetime.now().isoformat()),
    )


async def research(
    company_name: str,
    output_path: str | None = None,
    use_llm: bool = True,
) -> CompanyResearchOutput:
    """Run company research and return the result."""
    logger.info("Company research started: %s", company_name)
    raw_data = await _collect_data(company_name)

    data_sources: list[str] = []
    if raw_data["naver_news"].get("articles"):
        data_sources.append("naver_news")
    if raw_data["corp_info"] and "error" not in raw_data["corp_info"]:
        data_sources.append("corp_info")
    if raw_data["financial_info"] and "error" not in raw_data["financial_info"]:
        data_sources.append("financial_info")

    if not data_sources:
        logger.warning("No data collected: %s", company_name)
        return CompanyResearchOutput(
            company_name=company_name,
            summary="데이터를 수집할 수 없습니다.",
            researched_at=datetime.now().isoformat(),
        )

    if use_llm:
        result = synthesize_research(raw_data)
        result["data_sources"] = data_sources
        result["researched_at"] = datetime.now().isoformat()
    else:
        result = {
            "company_name": company_name,
            "data_sources": data_sources,
            "researched_at": datetime.now().isoformat(),
        }

    _save_result(company_name, result, output_path)

    if use_llm:
        return _dict_to_schema(result)

    return CompanyResearchOutput(
        company_name=company_name,
        data_sources=data_sources,
        researched_at=result["researched_at"],
    )
