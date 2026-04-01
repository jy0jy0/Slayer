# 김지호(@jy0jy0) — 전체 진행상황 정리

**최종 업데이트**: 2026-04-01
**브랜치**: `fix/code-hardening` (최신) / `feat/integration-v1`, `feat/agent-upgrade-v2` (머지 완료)

---

## 1. 구현 완료 기능

### Agent (LangGraph ReAct)

| Agent | 설명 | 도구 |
|-------|------|------|
| **기업 리서치** | 연구 전략을 LLM이 결정. 수집 후 검증 도구로 품질 판단 | `search_news`, `get_corp_info`, `get_financial_info`, `validate_research_data` |
| **이력서 최적화** | ATS 점수 목표까지 평가-최적화 반복. 임팩트 분석으로 전략 조정 | `evaluate_ats`, `optimize_blocks`, `analyze_optimization_impact` |
| **자기소개서 생성** | 5차원 품질 평가(키워드/톤/구조/구체성/기업맞춤) 기반 개선 | `generate_draft`, `review_and_refine`, `compute_stats`, `evaluate_draft_quality` |
| **JD-이력서 매칭** | 3단계 분석 (키워드→경력→종합갭) | `analyze_keywords`, `assess_experience_fit`, `identify_strategic_gaps` |

`create_react_agent` + `@tool` + 목표 기반 프롬프트. LLM이 도구 선택/순서/종료 시점을 결정.

### 공유 도구 레이어

| 도구 | 설명 | LLM 호출 |
|------|------|---------|
| `validate_research_data` | 수집 데이터 품질 검증 (완성도 점수, 누락 필드) | No (결정론적) |
| `validate_json_output` | JSON 출력 스키마 검증 | No (결정론적) |
| `get_cached_company_research` | DB 캐시 조회 (7일 TTL) | No |
| `analyze_optimization_impact` | 최적화 임팩트 분석 + diminishing returns 판단 | Yes |
| `evaluate_draft_quality` | 자기소개서 5차원 품질 평가 | Yes |

### Streamlit UI (6개 탭)

| 탭 | 기능 | 실시간 진행 |
|----|------|-----------|
| Dashboard | 기능 카드 5개 + Quick Start | - |
| Company Research | 회사명 → Agent → 카드형 결과 + DB 저장 | ✅ |
| JD-Resume Match | URL 파싱 / PDF 업로드 / JSON → ATS 점수 + 키워드 태그 + 바 차트 | ✅ |
| Resume Optimize | Before/After/Improvement 메트릭 + 변경사항 | ✅ |
| Cover Letter | 자기소개서 + 통계 + 핵심 포인트 | ✅ |
| Interview Prep | 6개 카테고리 면접질문 생성 | ✅ |

### 다른 팀원 기능 연동

| 팀원 기능 | 연동 | 상태 |
|-----------|------|------|
| 현지 — JD 파서 (`scrape_jd`) | UI URL 입력 → 자동 파싱 | ✅ |
| 예신 — 이력서 파서 (`parse_resume`) | UI PDF/DOCX 업로드 → 자동 파싱 | ✅ |
| 현지 — 면접 질문 생성 (`generate_interview_questions`) | UI 6번째 탭 | ✅ |

### DB 연동 (Supabase PostgreSQL)

| 항목 | 상태 |
|------|------|
| `save_company()` | ✅ 기업 리서치 → companies 테이블 |
| `save_match_result()` | ✅ 매칭 결과 → applications (실제 company_id 매핑) |
| `save_agent_log()` | ✅ 모든 Agent 실행 → agent_logs |
| Graceful skip | ✅ DATABASE_URL 미설정 시 UI 정상 동작 |

### 테스트

```
43 passed in 24s
```

| 테스트 파일 | 항목 수 | 내용 |
|------------|---------|------|
| `test_company_research.py` | 4 | 소스 클래스, Agent 빌드, 스키마 |
| `test_resume_optimizer.py` | 6 | Agent 빌드, 블록 변환, 조건 로직 |
| `test_cover_letter.py` | 2 | Agent 빌드, 스키마 |
| `test_jd_resume_matcher.py` | 2 | 목 데이터, 점수 상세 |
| `test_tools.py` | 16 | validate_research_data, validate_json_output, parse_agent_json |
| `test_resume_parser.py` (예신) | 13 | 포맷 감지, 추출, E2E |

---

## 2. 코드 품질 고도화 (04/01 작업)

### PR #17: Agent ReAct 고도화 (머지 완료)
- 4개 Agent 시스템 프롬프트: 절차 지시 → 목표 기반으로 리팩토링
- Resume Optimizer: **치명적 버그 수정** (최적화된 블록이 버려지던 문제)
- JD-이력서 매칭: 단일 LLM 호출 → 3-tool ReAct Agent로 전면 재작성
- 검증/품질 도구 5개 추가
- Gemini 코드 리뷰 4건 반영 (dict 타입 체크, 불필요 조건 제거, timezone 간결화)

### `fix/code-hardening` 브랜치 (PR 대기)

**Critical 3건 수정:**
1. JSON 파싱 크래시 — 4개 파일의 `_parse_final()` → 공용 `parse_agent_json()` 통일
2. optimize.py ResumeBlock 변환 깨짐 — Pydantic 모델에 `.get()` 호출 → 올바른 속성 접근
3. config.py `OPENAI_MODEL = "gpt-5-mini"` → `"gpt-4o-mini"` (실제 모델)

**High 5건 수정:**
4. Fallback ainvoke() IndexError 방지 — 빈 messages 안전 처리
5. save_match_result placeholder UUID → 실제 company_id 매핑
6. Silent `except: pass` → `logger.warning` (4개 UI 뷰)
7. 공용 JSON 파싱 함수 통일 (`slayer/llm.py`)
8. 도구 유닛 테스트 16개 추가

---

## 3. 기술 스택

| 항목 | 선택 |
|------|------|
| Agent 프레임워크 | LangGraph `create_react_agent` + `@tool` |
| LLM | OpenAI gpt-4o-mini (Agent), Gemini 2.5 Flash (파서/면접질문) |
| UI | Streamlit 1.55 + Plotly |
| DB | Supabase PostgreSQL (SQLAlchemy ORM) |
| 스키마 | Pydantic v2 (`slayer/schemas.py`) |
| 패키지 관리 | uv |
| 테마 | Deep Blue `#3b82f6` |

---

## 4. PR 현황

| PR | 제목 | 상태 |
|----|------|------|
| #8 | 프로젝트 구조 통합 | ✅ Merged |
| #9 | JD 파서 마이그레이션 (충돌 해결: 지호) | ✅ Merged |
| #10 | 면접 질문 생성기 (충돌 해결: 지호) | ✅ Merged |
| #12 | DB 스키마 + Supabase (예신) | ✅ Merged |
| #13 | 이력서 파싱 파이프라인 (예신) | ✅ Merged |
| #16 | 통합: Agent + UI + DB + 파서 연동 | ✅ Merged |
| #17 | Agent ReAct 고도화 (ReAct 고도화) | ✅ Merged |
| — | **코드 품질 고도화 (hardening)** | 🔄 `fix/code-hardening` |

---

## 5. 실행 방법

```bash
cd Slayer
source .venv/bin/activate
streamlit run slayer/ui/app.py
# → http://localhost:8501
```

### 환경 변수 (.env)
```
OPENAI_API_KEY=<required — Agent>
GOOGLE_API_KEY=<required — JD파서/이력서파서/면접질문>
NAVER_CLIENT_ID=<기업 뉴스>
NAVER_CLIENT_SECRET=<기업 뉴스>
DATA_GO_KR_API_KEY=<기업 기본정보/재무정보>
DATABASE_URL=<Supabase Transaction Pooler — optional>
SLAYER_LLM_MODEL=<optional — default: gpt-4o-mini>
```

---

## 6. 남은 작업

| 우선순위 | 작업 |
|---------|------|
| 🔴 | `fix/code-hardening` PR 제출 + 머지 |
| 🟡 | Agent recursion_limit 추가 (무한 루프 방지) |
| 🟡 | API 호출 retry 로직 (tenacity) |
| 🟡 | E2E 테스트 (실제 URL + PDF 전체 플로우) |
| 🟢 | 한글 주석 → 영문 통일 |
| 🟢 | 타입 힌트 보강 |
| 🟢 | 매직 스트링 → Enum 전환 |
