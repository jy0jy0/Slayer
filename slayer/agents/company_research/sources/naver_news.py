"""네이버 뉴스 검색 API 소스.

담당: 지호
마이그레이션: feat/company-research 에서 이동
"""

from __future__ import annotations

import html
import logging
import re

import httpx

from slayer.agents.company_research.source_base import BaseSource
from slayer.config import NAVER_CLIENT_ID, NAVER_CLIENT_SECRET, NAVER_NEWS_URL

logger = logging.getLogger(__name__)


def _strip_html(text: str) -> str:
    text = re.sub(r"<[^>]+>", "", text)
    return html.unescape(text).strip()


class NaverNewsSource(BaseSource):
    """네이버 뉴스 검색 API를 통해 기업 관련 뉴스를 수집한다."""

    @property
    def source_name(self) -> str:
        return "naver_news"

    async def fetch(self, company_name: str, **kwargs) -> dict:
        if not NAVER_CLIENT_ID or not NAVER_CLIENT_SECRET:
            logger.warning(
                "NAVER_CLIENT_ID 또는 NAVER_CLIENT_SECRET이 설정되지 않았습니다."
            )
            return {"articles": [], "error": "API 키 미설정"}

        headers = {
            "X-Naver-Client-Id": NAVER_CLIENT_ID,
            "X-Naver-Client-Secret": NAVER_CLIENT_SECRET,
        }
        params = {"query": company_name, "display": 10, "sort": "date"}

        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.get(
                    NAVER_NEWS_URL, headers=headers, params=params
                )
                resp.raise_for_status()
                data = resp.json()

            articles = []
            for item in data.get("items", []):
                articles.append(
                    {
                        "title": _strip_html(item.get("title", "")),
                        "description": _strip_html(item.get("description", "")),
                        "link": item.get("originallink") or item.get("link", ""),
                        "pub_date": item.get("pubDate", ""),
                    }
                )

            logger.info("네이버 뉴스 %d건 수집: %s", len(articles), company_name)
            return {"articles": articles}

        except httpx.HTTPStatusError as exc:
            logger.error(
                "네이버 뉴스 API 오류 (%d): %s", exc.response.status_code, exc
            )
            return {"articles": [], "error": f"HTTP {exc.response.status_code}"}
        except Exception as exc:
            logger.error("네이버 뉴스 수집 실패: %s", exc)
            return {"articles": [], "error": str(exc)}
