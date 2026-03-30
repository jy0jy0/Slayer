"""금융위원회 기업기본정보 API 소스.

담당: 지호
마이그레이션: feat/company-research 에서 이동
"""

from __future__ import annotations

import logging
from urllib.parse import quote

import httpx

from slayer.agents.company_research.source_base import BaseSource
from slayer.config import CORP_OUTLINE_URL, DATA_GO_KR_API_KEY

logger = logging.getLogger(__name__)


def _pick_best_match(items: list[dict], company_name: str) -> dict | None:
    """정확한 이름 매칭 우선, 없으면 직원 수 최대 기업 선택."""
    if not items:
        return None

    # 1) 정확 매칭
    for item in items:
        if item.get("corpNm", "").strip() == company_name.strip():
            return item

    # 2) 직원 수 최대
    def _emp_count(item: dict) -> int:
        try:
            return int(item.get("enpEmpeCnt", "0").replace(",", ""))
        except (ValueError, AttributeError):
            return 0

    return max(items, key=_emp_count)


class CorpInfoSource(BaseSource):
    """금융위원회 기업기본정보 API를 통해 기업 정보를 수집한다."""

    @property
    def source_name(self) -> str:
        return "corp_info"

    async def fetch(self, company_name: str, **kwargs) -> dict:
        if not DATA_GO_KR_API_KEY:
            logger.warning("DATA_GO_KR_API_KEY가 설정되지 않았습니다.")
            return {"error": "API 키 미설정"}

        params = {
            "serviceKey": DATA_GO_KR_API_KEY,
            "pageNo": "1",
            "numOfRows": "20",
            "resultType": "json",
            "corpNm": company_name,
        }

        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.get(CORP_OUTLINE_URL, params=params)
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

            if not items:
                logger.warning("기업 기본정보 조회 결과 없음: %s", company_name)
                return {"error": "조회 결과 없음"}

            best = _pick_best_match(items, company_name)
            if not best:
                return {"error": "매칭 기업 없음"}

            result = {
                "corp_name": best.get("corpNm", ""),
                "corp_name_en": best.get("corpEnsnNm", ""),
                "ceo": best.get("enpRprFnm", ""),
                "founded_date": best.get("enpBsadr", "") or best.get("enpFndt", ""),
                "employee_count": best.get("enpEmpeCnt", ""),
                "industry": best.get("enpMainBizNm", ""),
                "main_business": best.get("enpMainBizNm", ""),
                "address": best.get("enpBsadr", ""),
                "business_reg_no": best.get("enpTlno", "") or best.get("bzno", ""),
                "corp_reg_no": best.get("crno", ""),
                "exchange_listing_date": best.get("stacMm", ""),
                "kosdaq_listing_date": best.get("kosdaqMrktLstgDt", ""),
                "fss_corp_id": best.get("fssCrpId", ""),
            }

            logger.info("기업 기본정보 수집 완료: %s", company_name)
            return result

        except httpx.HTTPStatusError as exc:
            logger.error(
                "기업 기본정보 API 오류 (%d): %s", exc.response.status_code, exc
            )
            return {"error": f"HTTP {exc.response.status_code}"}
        except Exception as exc:
            logger.error("기업 기본정보 수집 실패: %s", exc)
            return {"error": str(exc)}
