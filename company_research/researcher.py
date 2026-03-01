from __future__ import annotations

import asyncio
import json
import logging
import re
from datetime import datetime
from pathlib import Path

from company_research.llm_client import synthesize_research
from company_research.sources.corp_info import CorpInfoSource
from company_research.sources.financial_info import FinancialInfoSource
from company_research.sources.naver_news import NaverNewsSource

logger = logging.getLogger(__name__)

OUTPUT_DIR = Path("research_output")


def _safe_filename(name: str) -> str:
    """파일명에 사용할 수 없는 문자 제거."""
    return re.sub(r'[\\/:*?"<>|]', "_", name)


async def _collect_data(company_name: str) -> dict:
    """모든 소스에서 데이터를 수집.

    네이버 뉴스 + 기업기본정보는 병렬 수집.
    재무정보는 기업기본정보의 crno 획득 후 순차 호출.
    """
    news_source = NaverNewsSource()
    corp_source = CorpInfoSource()
    financial_source = FinancialInfoSource()

    # 1단계: 네이버 뉴스 + 기업기본정보 병렬 수집
    news_task = asyncio.create_task(news_source.fetch(company_name))
    corp_task = asyncio.create_task(corp_source.fetch(company_name))

    news_data, corp_data = await asyncio.gather(news_task, corp_task)

    # 2단계: 기업기본정보에서 crno 획득 후 재무정보 순차 조회
    crno = corp_data.get("corp_reg_no", "")
    financial_data = {}
    if crno:
        financial_data = await financial_source.fetch(company_name, crno=crno)
    else:
        logger.info("crno 없음 — 재무정보 조회 건너뜀: %s", company_name)

    return {
        "naver_news": news_data,
        "corp_info": corp_data,
        "financial_info": financial_data,
    }


def _save_result(company_name: str, result: dict, output_path: str | None = None) -> str:
    """결과를 JSON 파일로 저장.

    Returns:
        저장된 파일 경로.
    """
    if output_path:
        path = Path(output_path)
    else:
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{_safe_filename(company_name)}_{timestamp}.json"
        path = OUTPUT_DIR / filename

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(result, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return str(path)


async def research(
    company_name: str,
    output_path: str | None = None,
    use_llm: bool = True,
) -> dict:
    """기업 리서치 전체 파이프라인 실행.

    Args:
        company_name: 리서치 대상 회사명.
        output_path: 결과 저장 경로 (None이면 research_output/에 자동 저장).
        use_llm: LLM 합성 사용 여부 (False면 raw 데이터만 반환).

    Returns:
        구조화된 기업 리서치 리포트 dict.
    """
    logger.info("기업 리서치 시작: %s", company_name)

    # 데이터 수집
    raw_data = await _collect_data(company_name)

    # 수집 소스 목록
    data_sources = []
    if raw_data["naver_news"].get("articles"):
        data_sources.append("naver_news")
    if raw_data["corp_info"] and "error" not in raw_data["corp_info"]:
        data_sources.append("corp_info")
    if raw_data["financial_info"] and "error" not in raw_data["financial_info"]:
        data_sources.append("financial_info")

    if not data_sources:
        logger.warning("수집된 데이터 없음: %s", company_name)
        return {
            "company_name": company_name,
            "error": "데이터를 수집할 수 없습니다.",
            "data_sources": [],
            "researched_at": datetime.now().isoformat(),
        }

    if use_llm:
        # LLM 합성
        result = synthesize_research(raw_data)
        result["data_sources"] = data_sources
        result["researched_at"] = datetime.now().isoformat()
    else:
        # raw 데이터 그대로 반환
        result = {
            "company_name": company_name,
            "raw_data": raw_data,
            "data_sources": data_sources,
            "researched_at": datetime.now().isoformat(),
        }

    # 저장
    saved_path = _save_result(company_name, result, output_path)
    logger.info("결과 저장: %s", saved_path)

    return result
