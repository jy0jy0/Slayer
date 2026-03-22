# Slayer — AI 기반 취업 지원 어시스턴트

## 팀

| 멤버 | GitHub | 담당 |
|------|--------|------|
| 지호 | @jy0jy0 | 기업 리서치, 이력서 최적화, 자기소개서 |
| 현지 | @hyeonjinnoh | JD 파싱, 면접 질문 |
| 예신 | @yesinkim | 이력서 파싱, Gmail 모니터, 프론트엔드, DB |

---

## 프로젝트 구조

```
Slayer/
├── slayer/                     # Python 백엔드
│   ├── schemas.py              # 공통 스키마 (Pydantic)
│   ├── config.py               # 공통 설정
│   ├── api/                    # FastAPI 엔드포인트
│   ├── db/                     # GCP PostgreSQL (9 tables)
│   ├── pipelines/              # 단일 패스 처리
│   │   ├── jd_parser/          # 현지 — JD 스크래핑+파싱
│   │   ├── resume_parser/      # 예신 — OCR 이력서 파싱
│   │   ├── gmail_monitor/      # 예신 — Gmail 폴링
│   │   ├── apply_pipeline/     # 예신 — 지원 액션
│   │   ├── interview_questions/# 현지 — 면접 질문 생성
│   │   └── jd_resume_matcher/  # TBD — 매칭 분석
│   ├── services/               # 공유 로직 (상태 전이 등)
│   └── agents/                 # 반복 루프 + 도구 호출
│       ├── company_research/   # 지호 (완료)
│       ├── resume_optimizer/   # 지호+현지
│       └── cover_letter/       # 지호
├── web/                        # React 프론트엔드 (예신)
├── supabase/                   # Google OAuth (예신)
├── data/                       # 테스트/샘플 데이터
│   ├── resumes/                # 이력서 PDF 5건
│   └── jds/                    # JD 샘플
└── tests/
```

### Pipeline vs Agent

| | Pipeline | Agent |
|---|---|---|
| 특징 | 고정 흐름, LLM 1회 | 반복 루프, 도구 호출, 조건 분기 |
| 해당 | JD 파싱, 이력서 파싱, 면접질문, Gmail, 지원액션 | 기업 리서치, 이력서 최적화, 자기소개서 |

---

## 데이터 흐름

```
[JD URL] ──→ JD 파싱 (현지) ──→ JDSchema ──────┐
                                                ├──→ MatchResult
[이력서] ──→ 이력서 파싱 (예신) ──→ ParsedResume ┘
                                                │
[회사명] ──→ 기업 리서치 (지호) ──→ CompanyResearchOutput
                                                │
              ┌─────────────────────────────────┘
              ▼                                 ▼
    이력서 최적화 Agent              자기소개서 생성 Agent
              │                                 │
              ▼                                 ▼
    ResumeOptimizationOutput        CoverLetterOutput
```

---

## 스키마

중앙 관리: `slayer/schemas.py` (Pydantic BaseModel)

| 스키마 | 생산자 | 소비자 |
|--------|--------|--------|
| `JDSchema` | JD 파싱 (현지) | 매칭, 최적화, 자소서, 면접질문 |
| `ParsedResume` | 이력서 파싱 (예신) | 매칭, 최적화, 자소서 |
| `MatchResult` | TBD — 매칭 | 최적화, 자소서 |
| `CompanyResearchOutput` | 기업 리서치 (지호) | 자소서, 면접질문 |
| `ResumeOptimizationOutput` | 최적화 (지호+현지) | 저장/다운로드 |
| `CoverLetterOutput` | 자소서 (지호) | 저장/다운로드 |

### ATS 점수 가중치

| 카테고리 | 가중치 |
|----------|--------|
| ats_simulation | 0.30 |
| keywords | 0.25 |
| experience | 0.20 |
| industry_specific | 0.15 |
| content | 0.05 |
| format | 0.03 |
| errors | 0.02 |

---

## DB (GCP PostgreSQL)

예신 설계. 9개 테이블: `users`, `resumes`, `companies`, `job_postings`, `applications`, `status_history`, `gmail_events`, `calendar_events`, `agent_logs`

스키마 상세: [Discussion #6](https://github.com/jy0jy0/Slayer/discussions/6#discussioncomment-16119302)

---

## 마이그레이션 가이드

### 지호 (`feat/company-research`)
```
company_research/  →  slayer/agents/company_research/
```

### 현지 (`feat/jd-scraper`)
```
slayer/parsers/*    →  slayer/pipelines/jd_parser/parsers/*
slayer/scraper.py   →  slayer/pipelines/jd_parser/scraper.py
slayer/cli.py       →  slayer/pipelines/jd_parser/cli.py
slayer/llm_client.py→  slayer/pipelines/jd_parser/llm_client.py
(+ parser_base.py, registry.py, __main__.py)
```

### 예신 (`feat/google-oauth-login`)
```
web/       →  변경 없음
supabase/  →  변경 없음
+ 새 작업: resume_parser, gmail_monitor, apply_pipeline, db/models.py
```

---

## Setup

```bash
# Python 환경
uv sync

# 환경 변수
cp .env.example .env
# .env 파일에 API 키 입력

# 개발 서버 (추후)
# uvicorn slayer.api.main:app --reload
```

---

## 논의 사항

1. JD-이력서 매칭 담당자 TBD
2. `skills` vs `requirements.required` 중복 정리 (현지)
3. 날짜 포맷 정규화 (`YYYY-MM`)
4. 오케스트레이션 프레임워크 (LangGraph 등) — MVP 이후
5. RAG + 벡터 DB (합격 이력서 검색) — MVP 이후
