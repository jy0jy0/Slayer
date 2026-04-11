"""Shared settings — API keys, model names, DB URL.

DRAFT - pending team review.

Module-specific settings live inside each module.
"""

from __future__ import annotations

import os

from dotenv import load_dotenv

load_dotenv()

# ── OpenAI ────────────────────────────────────────────────
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")
OPENAI_MODEL = "gpt-4o-mini"

# ── Google (Gemini + OAuth) ───────────────────────────────
GOOGLE_API_KEY = os.environ.get("GOOGLE_API_KEY", "")

# ── Naver News Search API ────────────────────────────────
NAVER_CLIENT_ID = os.environ.get("NAVER_CLIENT_ID", "")
NAVER_CLIENT_SECRET = os.environ.get("NAVER_CLIENT_SECRET", "")
NAVER_NEWS_URL = "https://openapi.naver.com/v1/search/news.json"

# ── Korea Public Data Portal ─────────────────────────────
DATA_GO_KR_API_KEY = os.environ.get("DATA_GO_KR_API_KEY", "")

# Korea FSC (Financial Services Commission) corporate outline API
CORP_OUTLINE_URL = (
    "https://apis.data.go.kr/1160100/service/"
    "GetCorpBasicInfoService_V2/getCorpOutline_V2"
)

# Korea FSC financial summary API (summary financial statements)
FINANCIAL_SUMMARY_URL = (
    "https://apis.data.go.kr/1160100/service/"
    "GetFinaStatInfoService_V2/getSummFinaStat_V2"
)

# ── GCP Database ─────────────────────────────────────────
DATABASE_URL = os.environ.get("DATABASE_URL", "")
