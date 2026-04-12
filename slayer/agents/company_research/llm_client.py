"""OpenAI LLM client (for company research).

Owner: Jiho
Migration: moved from feat/company-research branch.
Refactored to use slayer.llm.OpenAIProvider.
"""

from __future__ import annotations

import json
import logging

from slayer.llm import get_default_provider

logger = logging.getLogger(__name__)

SYNTHESIS_PROMPT = """당신은 한국 취업 준비생을 위한 기업 분석 전문가입니다.
아래 수집된 데이터를 분석하여 **구직자 관점의 기업 리서치 리포트**를 JSON으로 작성하세요.

## 규칙
1. 수집 데이터에 있는 정보만 사용하세요. 없는 정보를 추가하지 마세요.
2. 재무 수치는 원본 그대로 포함하세요.
3. summary는 구직자가 이 회사에 지원할 때 알아야 할 핵심 정보를 200-400자로 요약하세요.
4. 데이터가 없는 필드는 null로 두세요.
5. recent_news는 수집된 뉴스 기사를 그대로 포함하세요.

## 출력 JSON 구조
{
  "company_name": "회사명",
  "company_name_en": "영문명 (있으면)",
  "basic_info": {
    "industry": "업종", "ceo": "대표자명", "founded_date": "설립일",
    "employee_count": "직원 수", "headquarters": "주소",
    "business_registration_number": "사업자등록번호",
    "corp_registration_number": "법인등록번호",
    "listing_info": "상장 정보"
  },
  "financial_info": {
    "revenue": "매출액", "operating_profit": "영업이익", "net_income": "당기순이익",
    "total_assets": "총자산", "total_liabilities": "총부채", "capital": "자본금",
    "debt_ratio": "부채비율", "fiscal_year": "기준 사업연도"
  },
  "recent_news": [{"title": "...", "summary": "...", "source_url": "...", "published_date": "..."}],
  "summary": "구직자 관점 종합 요약 (200-400자)"
}

## 수집 데이터
"""


def synthesize_research(raw_data: dict) -> dict:
    """Synthesize raw collected data via LLM and return a structured research result."""
    provider = get_default_provider()
    prompt = SYNTHESIS_PROMPT + json.dumps(raw_data, ensure_ascii=False, indent=2)

    logger.info("LLM synthesis started")
    result_str = provider.generate_json(
        prompt, system_message="기업 분석 전문가. JSON만 출력."
    )
    result = json.loads(result_str)
    logger.info("LLM synthesis complete")
    return result
