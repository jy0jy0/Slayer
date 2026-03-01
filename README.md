# Slayer — 기업 리서치 도구

회사명을 입력하면 기업 기본정보, 재무정보, 최신 뉴스를 자동 수집하고 구직자 관점의 분석 리포트를 생성합니다.

## 설치

```bash
# Python 3.11+ 필요
uv sync
```

## 환경 설정

`.env` 파일에 API 키를 설정합니다.

```bash
# .env
OPENAI_API_KEY=sk-...
NAVER_CLIENT_ID=...
NAVER_CLIENT_SECRET=...
DATA_GO_KR_API_KEY=...
```

## 사용법

```bash
# 기본 실행 (JSON 리포트 출력 + research_output/에 자동 저장)
uv run python -m company_research "삼성전자"

# 지정 경로에 저장
uv run python -m company_research "카카오" -o kakao.json

# LLM 합성 없이 raw 데이터만 출력
uv run python -m company_research "네이버" --no-llm

# 상세 로그
uv run python -m company_research "삼성전자" -v
```

## 데이터 소스

| 소스 | API | 수집 내용 |
|------|-----|-----------|
| 네이버 뉴스 | Naver Search API | 최신 뉴스 10건 (제목, 요약, URL, 날짜) |
| 기업기본정보 | 공공데이터 포털 (금융위원회) | 회사명, 대표자, 설립일, 직원수, 주소, 법인등록번호 |
| 기업 재무정보 | 공공데이터 포털 (금융위원회) | 매출액, 영업이익, 당기순이익, 총자산, 부채비율 |

## 파일 구조

```
company_research/
├── __init__.py              — 패키지 버전 정보
├── __main__.py              — python -m company_research 실행 진입점
├── cli.py                   — Click 기반 CLI (인자 파싱, 로깅 설정, JSON 출력)
├── config.py                — 환경변수 로딩 및 API 엔드포인트 상수 정의
├── researcher.py            — 오케스트레이터: 소스 병렬 수집 → LLM 합성 → 파일 저장
├── llm_client.py            — OpenAI gpt-5-mini 클라이언트: raw 데이터를 구조화 리포트로 합성
├── source_base.py           — BaseSource ABC: 모든 데이터 소스의 추상 인터페이스
└── sources/
    ├── __init__.py
    ├── naver_news.py        — 네이버 뉴스 검색 API (httpx async, HTML 태그 제거)
    ├── corp_info.py         — 금융위원회 기업기본정보 API (회사명 매칭 + 직원수 폴백)
    └── financial_info.py    — 금융위원회 재무정보 API (crno 기반 요약재무제표, 연도 폴백)
```

### 핵심 모듈 상세

- **`researcher.py`**: `asyncio.gather()`로 네이버 뉴스 + 기업기본정보를 병렬 수집하고, 기업기본정보에서 획득한 법인등록번호(crno)로 재무정보를 순차 조회합니다. 수집 결과를 LLM에 전달하여 구직자 관점의 JSON 리포트를 생성합니다.
- **`llm_client.py`**: OpenAI `gpt-5-mini` 모델을 사용하며, `response_format=json_object`로 구조화된 출력을 보장합니다. 프롬프트에서 수집 데이터만 사용하도록 제한하여 hallucination을 방지합니다.
- **`source_base.py`**: `BaseSource(ABC)` 추상 클래스. `source_name` 프로퍼티와 `async fetch(company_name)` 메서드를 정의합니다. 새 데이터 소스 추가 시 이 인터페이스를 구현합니다.
- **`sources/corp_info.py`**: 회사명으로 검색 시 정확 매칭을 우선하고, 없으면 직원수가 가장 많은 법인을 선택합니다 (예: "삼성전자" → "삼성전자(주)" 매칭).
- **`sources/financial_info.py`**: 전년도 재무제표를 먼저 조회하고, 없으면 전전년도로 폴백합니다. crno가 없는 비상장/미등록 기업은 빈 결과를 반환합니다.

## 의존성

| 패키지 | 버전 | 용도 |
|--------|------|------|
| click | 8.2.1 | CLI 프레임워크 |
| httpx | 0.28.1 | 비동기 HTTP 클라이언트 |
| openai | 1.3.0 | OpenAI API 클라이언트 (gpt-5-mini) |
| python-dotenv | 1.0.0 | .env 파일 로딩 |
| pydantic | 2.11.4 | openai SDK 의존성 |
| anyio | 3.7.1 | 비동기 런타임 |

## 출력 예시

```json
{
  "company_name": "삼성전자(주)",
  "company_name_en": "SAMSUNG ELECTRONICS CO,.LTD",
  "basic_info": {
    "ceo": "전영현, 노태문",
    "founded_date": "19690113",
    "employee_count": "129480",
    "headquarters": "경기도 수원시 영통구 삼성로 129"
  },
  "financial_info": {
    "revenue": "300870903000000",
    "operating_profit": "32725961000000",
    "fiscal_year": "2024"
  },
  "recent_news": [...],
  "summary": "구직자 관점 종합 요약 (200-400자)",
  "data_sources": ["naver_news", "corp_info", "financial_info"],
  "researched_at": "2026-03-01T23:33:56"
}
```
