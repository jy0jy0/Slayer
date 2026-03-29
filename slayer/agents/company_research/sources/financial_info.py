"""금융위원회 재무정보 API 소스.

담당: 지호
마이그레이션: feat/company-research 에서 이동
"""

from __future__ import annotations

import logging
from datetime import datetime

import httpx

from slayer.agents.company_research.source_base import BaseSource
from slayer.config import DATA_GO_KR_API_KEY, FINANCIAL_SUMMARY_URL

logger = logging.getLogger(__name__)


def _extract_financial(items: list[dict]) -> dict | None:
    """재무제표 항목 리스트에서 가장 적합한 데이터를 추출한다.

    연결재무제표(ifrs-full) 우선, 없으면 개별재무제표 사용.
    """
    if not items:
        return None

    # 연결재무제표 우선
    consolidated = [
        it for it in items if it.get("fnstDivNm", "").startswith("연결")
    ]
    target = consolidated[0] if consolidated else items[0]

    return {
        "fiscal_year": target.get("bizYear", ""),
        "revenue": target.get("slsAmt", ""),
        "operating_profit": target.get("bztfPrfl", ""),
        "net_income": target.get("thstrntInc", ""),
        "total_assets": target.get("totalAst", ""),
        "total_liabilities": target.get("totalLblt", ""),
        "capital": target.get("cptl", ""),
        "debt_ratio": target.get("lbrtRt", ""),
        "statement_type": target.get("fnstDivNm", ""),
    }


class FinancialInfoSource(BaseSource):
    """금융위원회 요약재무제표 API를 통해 기업 재무정보를 수집한다."""

    @property
    def source_name(self) -> str:
        return "financial_info"

    async def fetch(self, company_name: str, **kwargs) -> dict:
        crno = kwargs.get("crno", "")
        if not crno:
            logger.warning("crno(법인등록번호)가 필요합니다: %s", company_name)
            return {"error": "crno 미제공"}

        if not DATA_GO_KR_API_KEY:
            logger.warning("DATA_GO_KR_API_KEY가 설정되지 않았습니다.")
            return {"error": "API 키 미설정"}

        # 현재 사업연도 → 전년도 순으로 시도
        current_year = datetime.now().year
        years_to_try = [str(current_year), str(current_year - 1)]

        for biz_year in years_to_try:
            params = {
                "serviceKey": DATA_GO_KR_API_KEY,
                "pageNo": "1",
                "numOfRows": "10",
                "resultType": "json",
                "crno": crno,
                "bizYear": biz_year,
            }

            try:
                async with httpx.AsyncClient(timeout=15.0) as client:
                    resp = await client.get(FINANCIAL_SUMMARY_URL, params=params)
                    resp.raise_for_status()
                    data = resp.json()

                body = data.get("response", {}).get("body", {})
                items_wrapper = body.get("items", {})

                if isinstance(items_wrapper, dict):
                    items = items_wrapper.get("item", [])
                elif isinstance(items_wrapper, list):
                    items = items_wrapper
                else:
                    items = []

                if isinstance(items, dict):
                    items = [items]

                if items:
                    result = _extract_financial(items)
                    if result:
                        logger.info(
                            "재무정보 수집 완료: %s (사업연도 %s)",
                            company_name,
                            biz_year,
                        )
                        return result

            except httpx.HTTPStatusError as exc:
                logger.error(
                    "재무정보 API 오류 (%d, 연도 %s): %s",
                    exc.response.status_code,
                    biz_year,
                    exc,
                )
            except Exception as exc:
                logger.error(
                    "재무정보 수집 실패 (연도 %s): %s", biz_year, exc
                )

        logger.warning("재무정보 조회 결과 없음: %s", company_name)
        return {"error": "조회 결과 없음"}
