"""Naver News Search API source.

Owner: Jiho
Migration: moved from feat/company-research branch.
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
    """Collect company-related news via the Naver News Search API."""

    @property
    def source_name(self) -> str:
        return "naver_news"

    async def fetch(self, company_name: str, **kwargs) -> dict:
        if not NAVER_CLIENT_ID or not NAVER_CLIENT_SECRET:
            logger.warning(
                "NAVER_CLIENT_ID or NAVER_CLIENT_SECRET is not configured."
            )
            return {"articles": [], "error": "API key not configured"}

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

            logger.info("Collected %d Naver news articles: %s", len(articles), company_name)
            return {"articles": articles}

        except httpx.HTTPStatusError as exc:
            logger.error(
                "Naver news API error (%d): %s", exc.response.status_code, exc
            )
            return {"articles": [], "error": f"HTTP {exc.response.status_code}"}
        except Exception as exc:
            logger.error("Naver news collection failed: %s", exc)
            return {"articles": [], "error": str(exc)}
