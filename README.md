# Slayer — AI 기반 취업 지원 어시스턴트

채용공고 URL 과 이력서 한 부만 있으면, **JD 분석 → 매칭 → 이력서 최적화 → 자기소개서 작성 → 면접 질문 → 기업 리서치** 까지 한 번에 준비해주는 LLM 기반 도구입니다.

---

## 팀

| 멤버 | GitHub | 담당 |
|------|--------|------|
| 신현지 | [@shinhyunji36](https://github.com/shinhyunji36) | JD 파싱 (잡코리아·원티드 + 멀티 직무 추출), 면접 질문 (피드백 / 재생성 / DOCX) |
| 김예신 | [@yesinkim](https://github.com/yesinkim) | DB 스키마, 이력서 파싱 (PyMuPDF + Gemini), Gmail 모니터, FastAPI, React 프론트엔드 |
| 김지호 | [@jy0jy0](https://github.com/jy0jy0) | 기업 리서치, 이력서 최적화, 자기소개서, Streamlit UI 통합, Agent 하드닝 |

---

## 빠른 시작

```bash
# 1. 의존성 설치
uv sync

# 2. 환경 변수 설정 — .env.example 의 키 채우기
cp .env.example .env

# 3. Streamlit UI 실행
streamlit run slayer/ui/app.py
```

브라우저에서 http://localhost:8501 접속 후 좌측 탭 순서대로 진행하면 됩니다.

### 필수 / 선택 환경 변수

| 키 | 용도 | 필수 |
|---|---|---|
| `OPENAI_API_KEY` | ReAct Agent (매칭 / 최적화 / 자소서 / 기업리서치) | ✅ |
| `GOOGLE_API_KEY` | 이력서 / JD 파싱 + 면접질문 (Gemini), OpenAI 미설정 시 매칭 폴백 | ✅ |
| `NAVER_CLIENT_ID` / `NAVER_CLIENT_SECRET` | 기업 뉴스 검색 | 권장 |
| `DATA_GO_KR_API_KEY` | 기업 기본정보 / 재무정보 (공공데이터포털) | 권장 |
| `DATABASE_URL` | Supabase PostgreSQL — 결과 저장 | 선택 (없어도 UI 동작) |

---

## 주요 기능

| 기능 | 입력 | 출력 | 담당 |
|---|---|---|---|
| **JD 파싱** | 잡코리아 / 원티드 URL | `JDSchema` (회사·직무·요구사항·스킬) | 현지 |
| **이력서 파싱** | PDF / DOCX / TXT / JSON | `ParsedResume` (인적사항·경력·스킬·경력연수) | 예신 |
| **JD ↔ 이력서 매칭** | JD + 이력서 | `MatchResult` (ATS 점수, 매칭/누락 키워드, 강·약점) | 지호 |
| **이력서 최적화** | JD + 이력서 + 매칭 결과 | `ResumeOptimizationOutput` (블록별 변경 + 최종 ATS 점수) | 지호 |
| **자기소개서 생성** | JD + 이력서 + 매칭 + 기업 리서치 | `CoverLetterOutput` (본문 + 핵심 포인트 + 키워드 커버리지) | 지호 |
| **기업 리서치** | 회사명 | `CompanyResearchOutput` (기본정보·재무·뉴스 10건) | 지호 |
| **면접 질문 생성** | 위 결과 일체 | 6개 카테고리 × N개 질문 + 예시 답변 + 우선 대비 영역 | 현지 |

각 기능은 Streamlit UI 의 별도 탭에서 단독 사용 가능합니다.

---

## 데이터 흐름

```
[JD URL] ──→ JD 파싱 ──→ JDSchema ─┐
                                    ├──→ 매칭 ──→ MatchResult ─┐
[이력서] ──→ 이력서 파싱 ──→ ParsedResume ┘                      │
                                    │                            │
[회사명] ──→ 기업 리서치 ──→ CompanyResearchOutput              │
                                    │                            │
                                    │           ┌────────────────┤
                                    │           ▼                ▼
                                    │      이력서 최적화     자기소개서
                                    │           │                │
                                    └───────────┴────────┐       ▼
                                                          ▼  CoverLetterOutput
                                                    면접 질문 생성
                                                          │
                                                          ▼
                                                InterviewQuestionsOutput
```

---

## 아키텍처

### Pipeline vs Agent

이 프로젝트의 LLM 모듈은 두 가지 패턴으로 나뉩니다.

|  | Pipeline | Agent (ReAct) |
|---|---|---|
| 흐름 | 고정 단계, LLM 1회 호출 | LLM 이 도구 호출 / 종료 시점을 자율 결정 |
| 사용 모듈 | JD 파싱 / 이력서 파싱 / 면접질문 / Gmail / 지원 액션 | 기업 리서치 / 매칭 / 이력서 최적화 / 자기소개서 |
| 구현 | 함수 호출 + 후처리 | LangGraph `create_react_agent` |

### 디렉토리 구조

```
Slayer/
├── slayer/
│   ├── schemas.py              # 모듈 간 공통 Pydantic 스키마
│   ├── llm.py                  # OpenAI / Gemini 공통 Provider + retry decorator
│   ├── ui/                     # Streamlit 앱 (탭별 view)
│   ├── agents/                 # ReAct Agent (LangGraph)
│   │   ├── company_research/
│   │   ├── resume_optimizer/
│   │   └── cover_letter/
│   ├── pipelines/              # 단일 패스 처리
│   │   ├── jd_parser/          # 잡코리아·원티드 파서 + multi-role 추출
│   │   ├── resume_parser/      # PyMuPDF + Gemini 구조화
│   │   ├── jd_resume_matcher/  # ReAct (실은 Agent, 진입점은 pipelines/)
│   │   ├── interview_questions/
│   │   ├── gmail_monitor/
│   │   └── apply_pipeline/
│   ├── api/                    # FastAPI 엔드포인트
│   ├── db/                     # Supabase PostgreSQL + Alembic 마이그레이션
│   └── services/               # 상태 전이 등 공유 로직
├── web/                        # React 프론트엔드 (Vite + TS)
├── tests/                      # pytest (75+ 케이스)
├── docs/                       # 파이프라인별 문서, 회의 자료
├── data/                       # 샘플 이력서 / JD
└── scripts/                    # 로컬 실행 스크립트
```

### 핵심 스키마 (`slayer/schemas.py`)

| 스키마 | 생산자 | 소비자 |
|---|---|---|
| `JDSchema` | JD 파서 | 매칭 / 최적화 / 자소서 / 면접질문 |
| `ParsedResume` | 이력서 파서 | 매칭 / 최적화 / 자소서 / 면접질문 |
| `MatchResult` | 매칭 Agent | 최적화 / 자소서 / 면접질문 |
| `CompanyResearchOutput` | 기업리서치 Agent | 자소서 / 면접질문 |
| `ResumeOptimizationOutput` | 최적화 Agent | UI 표시 / DB 저장 |
| `CoverLetterOutput` | 자소서 Agent | UI 표시 / DB 저장 |
| `InterviewQuestionsOutput` | 면접질문 파이프라인 | UI 표시 / DOCX 다운로드 / DB 저장 |

### ATS 점수 가중치

매칭 단계에서 종합 점수를 계산할 때 사용하는 가중치입니다.

| 카테고리 | 가중치 |
|---|---|
| ats_simulation | 0.30 |
| keywords | 0.25 |
| experience | 0.20 |
| industry_specific | 0.15 |
| content | 0.05 |
| format | 0.03 |
| errors | 0.02 |

---

## DB (Supabase PostgreSQL)

10 개 테이블 + Alembic 마이그레이션. 결과 저장은 자동 (DB 미설정 시 UI 만 사용 가능).

| 테이블 | 용도 |
|---|---|
| `users` | 사용자 |
| `resumes` | 파싱된 이력서 |
| `companies` | 회사 마스터 (기업리서치 결과 포함) |
| `job_postings` | JD 파싱 결과 |
| `applications` | 지원 1건 = 매칭 / 최적화 / 자소서 / 면접질문 결과 묶음 |
| `application_stages` | 전형 단계별 상태 |
| `status_history` | 상태 변경 이력 |
| `gmail_events` | Gmail 모니터가 분류한 메일 |
| `calendar_events` | 면접 일정 등 |
| `agent_logs` | Agent 실행 로그 |

상세 스키마: [`docs/data-schema.md`](docs/data-schema.md)
