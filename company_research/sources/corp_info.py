from __future__ import annotations

import logging

import httpx

from company_research.config import CORP_OUTLINE_URL, DATA_GO_KR_API_KEY
from company_research.source_base import BaseSource

logger = logging.getLogger(__name__)


class CorpInfoSource(BaseSource):
    """금융위원회 기업기본정보 - 기업개요 조회."""

    @property
    def source_name(self) -> str:
        return "corp_info"

    async def fetch(self, company_name: str, **kwargs) -> dict:
        """회사명으로 기업개요 조회.

        Returns:
            기업개요 dict. crno(법인등록번호)를 포함하여 재무정보 조회에 활용.
            검색 결과 없으면 빈 dict.
        """
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
            items = body.get("items", {}).get("item", [])

            if not items:
                logger.info("기업기본정보 검색 결과 없음: %s", company_name)
                return {}

            if not isinstance(items, list):
                items = [items]

            # 정확히 일치하는 회사명 우선, 없으면 직원수가 가장 많은 결과
            item = None
            for candidate in items:
                if candidate.get("corpNm", "") == company_name:
                    item = candidate
                    break

            if item is None:
                # 정확 매칭 없으면 직원수 기준 정렬 (가장 큰 법인 선택)
                items.sort(
                    key=lambda x: int(x.get("enpEmpeCnt") or 0),
                    reverse=True,
                )
                item = items[0]

            result = {
                "corp_name": item.get("corpNm", ""),
                "corp_name_en": item.get("corpEnsnNm", ""),
                "ceo": item.get("enpRprFnm", ""),
                "founded_date": item.get("enpEstbDt", ""),
                "employee_count": item.get("enpEmpeCnt", ""),
                "industry": item.get("sicNm", ""),
                "main_business": item.get("enpMainBizNm", ""),
                "address": item.get("enpBsadr", ""),
                "business_reg_no": item.get("bzno", ""),
                "corp_reg_no": item.get("crno", ""),
                "exchange_listing_date": item.get("enpXchgLstgDt", ""),
                "kosdaq_listing_date": item.get("enpKosdaqLstgDt", ""),
                "fss_corp_id": item.get("fssCorpUnqNo", ""),
            }

            logger.info("기업기본정보 수집 완료: %s (crno=%s)", company_name, result["corp_reg_no"])
            return result

        except httpx.HTTPStatusError as exc:
            logger.error("기업기본정보 API 오류 (%d): %s", exc.response.status_code, exc)
            return {"error": f"HTTP {exc.response.status_code}"}
        except Exception as exc:
            logger.error("기업기본정보 수집 실패: %s", exc)
            return {"error": str(exc)}
