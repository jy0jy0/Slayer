"""Korea FSC corporate outline API source.

Owner: Jiho
Migration: moved from feat/company-research branch.
"""

from __future__ import annotations

import logging
from urllib.parse import quote

import httpx

from slayer.agents.company_research.source_base import BaseSource
from slayer.config import CORP_OUTLINE_URL, DATA_GO_KR_API_KEY

logger = logging.getLogger(__name__)


def _pick_best_match(items: list[dict], company_name: str) -> dict | None:
    """Prefer exact name match; otherwise pick the entry with the largest employee count."""
    if not items:
        return None

    # 1) Exact match
    for item in items:
        if item.get("corpNm", "").strip() == company_name.strip():
            return item

    # 2) Largest employee count
    def _emp_count(item: dict) -> int:
        try:
            return int(item.get("enpEmpeCnt", "0").replace(",", ""))
        except (ValueError, AttributeError):
            return 0

    return max(items, key=_emp_count)


class CorpInfoSource(BaseSource):
    """Collect corporate information via the Korea FSC corporate outline API."""

    @property
    def source_name(self) -> str:
        return "corp_info"

    async def fetch(self, company_name: str, **kwargs) -> dict:
        if not DATA_GO_KR_API_KEY:
            logger.warning("DATA_GO_KR_API_KEY is not configured.")
            return {"error": "API key not configured"}

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
                logger.warning("No corporate info results: %s", company_name)
                return {"error": "No results"}

            best = _pick_best_match(items, company_name)
            if not best:
                return {"error": "No matching company"}

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

            logger.info("Corporate info collection complete: %s", company_name)
            return result

        except httpx.HTTPStatusError as exc:
            logger.error(
                "Corporate info API error (%d): %s", exc.response.status_code, exc
            )
            return {"error": f"HTTP {exc.response.status_code}"}
        except Exception as exc:
            logger.error("Corporate info collection failed: %s", exc)
            return {"error": str(exc)}
