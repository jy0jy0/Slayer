from __future__ import annotations

import logging
from datetime import datetime

import httpx

from company_research.config import DATA_GO_KR_API_KEY, FINANCIAL_SUMMARY_URL
from company_research.source_base import BaseSource

logger = logging.getLogger(__name__)


class FinancialInfoSource(BaseSource):
    """금융위원회 기업 재무정보 - 요약재무제표 조회."""

    @property
    def source_name(self) -> str:
        return "financial_info"

    async def fetch(self, company_name: str, **kwargs) -> dict:
        """법인등록번호(crno)로 요약재무제표 조회.

        Args:
            company_name: 회사명 (로깅용).
            **kwargs:
                crno: 법인등록번호 (필수, corp_info에서 획득).

        Returns:
            재무 요약 dict. crno 미제공 시 빈 dict.
        """
        crno = kwargs.get("crno", "")
        if not crno:
            logger.info("crno 미제공 — 재무정보 조회 건너뜀: %s", company_name)
            return {}

        if not DATA_GO_KR_API_KEY:
            logger.warning("DATA_GO_KR_API_KEY가 설정되지 않았습니다.")
            return {"error": "API 키 미설정"}

        # 최근 사업연도 (전년도)
        biz_year = str(datetime.now().year - 1)

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
            items = body.get("items", {}).get("item", [])

            if not items:
                # 전년도 데이터 없으면 전전년도 시도
                prev_year = str(int(biz_year) - 1)
                params["bizYear"] = prev_year
                async with httpx.AsyncClient(timeout=15.0) as client:
                    resp = await client.get(FINANCIAL_SUMMARY_URL, params=params)
                    resp.raise_for_status()
                    data = resp.json()

                body = data.get("response", {}).get("body", {})
                items = body.get("items", {}).get("item", [])
                biz_year = prev_year

            if not items:
                logger.info("재무정보 없음: %s (crno=%s)", company_name, crno)
                return {}

            # 첫 번째 항목 사용
            item = items[0] if isinstance(items, list) else items

            result = {
                "fiscal_year": biz_year,
                "revenue": item.get("enpSaleAmt", ""),
                "operating_profit": item.get("enpBzopPft", ""),
                "net_income": item.get("enpCrtmNpf", ""),
                "total_assets": item.get("enpTastAmt", ""),
                "total_liabilities": item.get("enpTdbtAmt", ""),
                "capital": item.get("enpCptlAmt", ""),
                "debt_ratio": item.get("fnclDebtRto", ""),
                "statement_type": item.get("fnclDcdNm", ""),
            }

            logger.info("재무정보 수집 완료: %s (%s년)", company_name, biz_year)
            return result

        except httpx.HTTPStatusError as exc:
            logger.error("재무정보 API 오류 (%d): %s", exc.response.status_code, exc)
            return {"error": f"HTTP {exc.response.status_code}"}
        except Exception as exc:
            logger.error("재무정보 수집 실패: %s", exc)
            return {"error": str(exc)}
