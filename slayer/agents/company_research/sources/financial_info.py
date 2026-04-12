"""Korea FSC financial summary API source.

Owner: Jiho
Migration: moved from feat/company-research branch.
"""

from __future__ import annotations

import logging
from datetime import datetime

import httpx

from slayer.agents.company_research.source_base import BaseSource
from slayer.config import DATA_GO_KR_API_KEY, FINANCIAL_SUMMARY_URL

logger = logging.getLogger(__name__)


def _extract_financial(items: list[dict]) -> dict | None:
    """Extract the most suitable entry from a list of financial statement items.

    Prefer consolidated statements (ifrs-full); fall back to separate statements.
    """
    if not items:
        return None

    # Prefer consolidated statements ("연결" marks consolidated in the source API)
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
    """Collect corporate financial data via the Korea FSC summary financial-statement API."""

    @property
    def source_name(self) -> str:
        return "financial_info"

    async def fetch(self, company_name: str, **kwargs) -> dict:
        crno = kwargs.get("crno", "")
        if not crno:
            logger.warning("crno (corporate registration number) is required: %s", company_name)
            return {"error": "crno not provided"}

        if not DATA_GO_KR_API_KEY:
            logger.warning("DATA_GO_KR_API_KEY is not configured.")
            return {"error": "API key not configured"}

        # Try the current fiscal year first, then fall back to the previous year.
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
                            "Financial info collection complete: %s (fiscal year %s)",
                            company_name,
                            biz_year,
                        )
                        return result

            except httpx.HTTPStatusError as exc:
                logger.error(
                    "Financial info API error (%d, year %s): %s",
                    exc.response.status_code,
                    biz_year,
                    exc,
                )
            except Exception as exc:
                logger.error(
                    "Financial info collection failed (year %s): %s", biz_year, exc
                )

        logger.warning("No financial info results: %s", company_name)
        return {"error": "No results"}
