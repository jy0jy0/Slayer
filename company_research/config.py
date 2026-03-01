from __future__ import annotations

import os

from dotenv import load_dotenv

load_dotenv()

# ── OpenAI ────────────────────────────────────────────────
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")
OPENAI_MODEL = "gpt-5-mini"

# ── 네이버 뉴스 검색 API ─────────────────────────────────
NAVER_CLIENT_ID = os.environ.get("NAVER_CLIENT_ID", "")
NAVER_CLIENT_SECRET = os.environ.get("NAVER_CLIENT_SECRET", "")
NAVER_NEWS_URL = "https://openapi.naver.com/v1/search/news.json"

# ── 공공데이터 포털 ──────────────────────────────────────
DATA_GO_KR_API_KEY = os.environ.get("DATA_GO_KR_API_KEY", "")

# 금융위원회 기업기본정보
CORP_OUTLINE_URL = (
    "https://apis.data.go.kr/1160100/service/"
    "GetCorpBasicInfoService_V2/getCorpOutline_V2"
)

# 금융위원회 기업 재무정보 (요약재무제표)
FINANCIAL_SUMMARY_URL = (
    "https://apis.data.go.kr/1160100/service/"
    "GetFinaStatInfoService_V2/getSummFinaStat_V2"
)
