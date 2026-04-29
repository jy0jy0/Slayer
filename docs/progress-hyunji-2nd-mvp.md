# Slayer — 현지 기여 현황 & 2차 MVP 계획

> 작성일: 2026-04-12 | 담당: shinhyunji36

---

## 1. 프로젝트 전체 브랜치 현황

| 브랜치 | 상태 | 담당 | 설명 |
|---|---|---|---|
| `main` | 기준 | 전체 | 1차 MVP 통합 완료 |
| `feat/jd-parser-ui` | **작업 중 (미머지)** | 현지 | JD Parser UI + 멀티-직무 파싱 개선 |
| `feat/interview-question-generator` | 로컬 (main 머지됨) | 현지 | 면접 질문 생성 파이프라인 |
| `feat/jd-scraper` | 로컬 (main 머지됨) | 현지 | JD 스크래퍼 초기 버전 |
| `remotes/origin/feat/agent-upgrade-v2` | 원격 | 지호 | 에이전트 ReAct 업그레이드 |
| `remotes/origin/feat/company-research` | 원격 | 지호 | 기업 리서치 에이전트 |
| `remotes/origin/feat/company-research-resume-optimizer` | 원격 | 지호 | 리서치 + 이력서 최적화 통합 |
| `remotes/origin/feat/google-oauth-login` | 원격 | 예신 | Google OAuth 로그인 |
| `remotes/origin/feat/integration-v1` | 원격 | 전체 | 1차 통합 브랜치 |
| `remotes/origin/fix/code-hardening` | 원격 (머지됨) | 지호 | 보안 강화 9건 해결 |

---

## 2. shinhyunji36 기여 내역

### 2-1. main에 머지된 것

| 커밋 | 내용 |
|---|---|
| `feat(jobkorea): Gemini 멀티모달 기반 JD 파이프라인` | 이미지 기반 공고를 Gemini Vision으로 직접 파싱 |
| `feat: Wanted 파서 LLM 기반 리팩토링` | 정규식 → LLM 파싱으로 전환, 안정성 향상 |
| `feat: --job-title 필터 + position 필드` | 공고 내 직무명 필터링, position 필드 추가 |
| `feat: 면접 질문 생성 파이프라인` | JD + 이력서 + 기업 리서치 + 매칭 결과 → 6개 카테고리 질문 생성 |
| `feat: JD 파서 프로젝트 구조 마이그레이션` | 전체 구조 통합에 맞춰 JD 파서 재편 |
| `fix: LLM JSON 파싱 오류 처리` | 의존성 버전 상한선 추가, 안정성 개선 |

### 2-2. 현재 브랜치 (`feat/jd-parser-ui`) — 미머지

| 파일 | 변경 내용 |
|---|---|
| `slayer/ui/views/jd_parser.py` (신규) | URL 입력 → 크롤 → LLM 파싱 → 인라인 편집 → DB 저장 전체 Streamlit UI |
| `slayer/ui/app.py` | 사이드바에 JD Parser 페이지 추가 |
| `slayer/pipelines/jd_parser/section_extractor.py` (신규) | 멀티-직무 공고에서 목표 직무 섹션만 슬라이싱 (텍스트 기반) |
| `slayer/pipelines/jd_parser/parser_base.py` | `ParseResult` 컨테이너 추가 — JD + suspicious_items + image_urls |
| `slayer/pipelines/jd_parser/scraper.py` | `ParseResult` 반환 처리, Windows asyncio 호환성 (`WindowsProactorEventLoopPolicy`) |
| `slayer/schemas.py` | `experience` 기본값 validator, `deadline` 날짜 정규화 validator 추가 |
| `slayer/pipelines/jd_resume_matcher/matcher.py` | `assess_experience_fit`에 `responsibilities` 컨텍스트 추가 (매칭 정확도 향상) |
| `slayer/db/repository.py` | `get_cached_job_posting`, `update_job_posting` 함수 추가 |
| `docs/pipelines/jd_parser_multi_role.md` (신규) | 멀티-직무 처리 흐름 mermaid 다이어그램 + 설계 문서 |

---

## 3. 당장 마무리해야 할 것

현재 `feat/jd-parser-ui` 브랜치의 변경 사항이 **전부 uncommitted** 상태이다.

### 체크리스트

- [ ] `streamlit run slayer/ui/app.py` — JD Parser 탭 동작 검증
- [ ] `pytest tests/pipelines/test_jd_parser.py tests/pipelines/test_section_extractor.py`
- [ ] untracked 파일 스테이징 (`jd_parser.py`, `section_extractor.py`, `docs/pipelines/jd_parser_multi_role.md`, `create_tables.py` 등 필요한 것만)
- [ ] 커밋 & PR 생성 → main 머지

---

## 4. 2차 MVP 기여 계획 — AI Agent Engineer 역량 기반

### 배경: AI Agent Engineer가 요구하는 핵심 역량

취업 공고에서 공통적으로 요구하는 기술 스택:

| 역량 | 관련 기술 |
|---|---|
| **LangGraph** — 멀티에이전트, StateGraph, 조건부 엣지, 체크포인터 | LangGraph, LangChain |
| **Tool Calling** — LLM이 외부 도구를 스스로 호출하는 ReAct 패턴 | OpenAI function calling, LangChain tools |
| **RAG** — 벡터 DB + 임베딩 기반 컨텍스트 검색 | pgvector, FAISS, ChromaDB |
| **에이전트 메모리** — 단기(세션), 장기(DB) 메모리 관리 | LangGraph checkpointer, Supabase |
| **비동기 파이썬** — async/await, 이벤트 루프 제어 | asyncio, concurrent.futures |
| **스트리밍 응답** — LLM 응답을 토큰 단위로 UI에 표시 | `astream`, Streamlit `st.write_stream` |
| **에이전트 평가/관측** — LangSmith 트레이싱, 품질 지표 | LangSmith, 커스텀 평가 로직 |
| **프롬프트 엔지니어링** — 구조화된 출력, Few-shot, CoT | Pydantic structured output |

---

### 4-1. 면접 시뮬레이션 Agent (최우선 — 임팩트 最大)

**현재 상태**: `interview_prep.py`는 버튼 한 번으로 질문 목록을 생성하고 끝나는 **단방향 파이프라인**이다.

**목표**: 사용자와 실시간으로 **대화하는 면접 시뮬레이터 Agent**로 전환한다.

```
사용자: "안녕하세요, 지원 동기를 말씀해주세요."
Agent:  [사용자 답변 평가] → [다음 꼬리 질문 생성] → "방금 말씀하신 ~~ 프로젝트에서 구체적으로..."
```

**경험할 수 있는 역량**:

| 역량 | 구현 방법 |
|---|---|
| **LangGraph StateGraph** | `InterviewState` 정의 → `ask_question` → `evaluate_answer` → `decide_next` 노드 |
| **LangGraph 체크포인터 (단기 메모리)** | `MemorySaver` 로 대화 히스토리 유지 — 세션 내 이전 답변을 기억해 꼬리 질문 생성 |
| **조건부 엣지** | 답변 품질 평가 → 꼬리 질문 / 다음 카테고리 / 종료 분기 |
| **스트리밍 응답** | `agent.astream()` + Streamlit `st.write_stream` 으로 타이핑 효과 |
| **Tool Calling** | `evaluate_answer(answer, question, jd_context)` 도구를 LLM이 직접 호출 |

**구현 파일**:
- `slayer/agents/interview_simulator/agent.py` — LangGraph StateGraph
- `slayer/agents/interview_simulator/tools.py` — evaluate_answer, generate_followup_question
- `slayer/ui/views/interview_prep.py` — 시뮬레이션 모드 추가 (생성 모드와 탭 분리)

---

### 4-2. JD 중복 감지 — pgvector RAG 패턴 (RAG 경험)

**현재 상태**: 같은 공고를 두 번 파싱하면 DB에 중복 저장되거나 단순 URL 일치만 확인한다.

**목표**: 공고 임베딩을 pgvector에 저장하고, 새 공고 파싱 전 유사 공고를 벡터 검색으로 찾아낸다.

```
새 URL 입력 → JD 텍스트 임베딩 → pgvector 유사도 검색 → 유사 공고 있으면 경고/재사용 제안
```

**경험할 수 있는 역량**:

| 역량 | 구현 방법 |
|---|---|
| **RAG 기본 패턴** | 임베딩 생성 → 벡터 저장 → 유사도 검색 (cosine similarity) |
| **pgvector** | Supabase가 이미 PostgreSQL — `pgvector` 확장 활성화, `VECTOR` 컬럼 추가 |
| **임베딩 모델** | OpenAI `text-embedding-3-small` or Google `text-embedding-004` |
| **구조화된 Retriever** | `repository.py`에 `find_similar_jd(embedding, threshold=0.9)` 추가 |

**구현 파일**:
- `slayer/db/models.py` — `JobPosting`에 `embedding VECTOR(1536)` 컬럼 추가
- `slayer/db/repository.py` — `upsert_jd_embedding`, `find_similar_jd` 함수
- `slayer/pipelines/jd_parser/scraper.py` — 스크래핑 후 임베딩 저장 훅

---

### 4-3. 면접 질문 생성을 ReAct Agent로 전환 (Tool Calling 심화)

**현재 상태**: `generator.py`는 단일 LLM 호출로 모든 질문을 한 번에 생성한다. 이는 **파이프라인**이지 **에이전트**가 아니다.

**목표**: LLM이 스스로 도구를 선택하며 단계별로 질문을 생성하는 ReAct Agent로 전환한다.

```
Agent: "기술 카테고리 질문을 만들기 위해 먼저 JD 스킬과 이력서 스킬을 비교하겠습니다."
       → [tool: compare_skills(jd_skills, resume_skills)]
       → "missing_keywords: Kubernetes, Airflow 확인. 이제 질문을 생성합니다."
       → [tool: generate_questions(category="기술", focus=["Kubernetes", "Airflow"])]
```

**경험할 수 있는 역량**:

| 역량 | 구현 방법 |
|---|---|
| **LangGraph ReAct** | `create_react_agent` 또는 커스텀 StateGraph |
| **도메인 특화 Tool 설계** | `compare_skills`, `search_interview_trends`, `validate_question_quality` 도구 |
| **멀티-스텝 추론** | 각 카테고리를 별도 단계로 나눠 LLM이 순서 결정 |
| **LangSmith 트레이싱** | 각 도구 호출 로그 → 어떤 reasoning으로 어떤 tool을 골랐는지 추적 |

**구현 파일**:
- `slayer/agents/interview_question_agent/agent.py`
- `slayer/agents/interview_question_agent/tools.py`

---

### 4-4. 사람인(Saramin) 파서 추가 (파이프라인 완성)

**현재 상태**: Jobkorea, Wanted 두 플랫폼만 지원. 국내 3대 채용 플랫폼 중 하나 누락.

**목표**: `slayer/pipelines/jd_parser/parsers/saramin.py` 구현.

**경험할 수 있는 역량**:
- 새 플랫폼의 HTML 구조 분석 및 크롤 전략 설계
- `BaseParser` 추상 인터페이스 확장 패턴
- `section_extractor` 멀티-직무 처리 적용 여부 판단

---

### 4-5. 에이전트 관측성 강화 (LangSmith + 커스텀 평가)

**현재 상태**: `save_agent_log`로 기본 성공/실패만 기록. 에이전트 내부 추론 추적 없음.

**목표**: LangSmith 트레이싱을 면접 질문 에이전트에 붙이고, 질문 품질 자동 평가 로직 추가.

```python
# 자동 평가 예시
evaluator = QuestionQualityEvaluator()
score = evaluator.evaluate(question, jd_context)  # 관련성, 구체성, 난이도 점수
```

**경험할 수 있는 역량**:
- LangSmith `@traceable` 데코레이터
- 커스텀 `EvaluationResult` 스키마 설계
- LLM-as-judge 패턴 (다른 LLM이 생성된 질문을 평가)

---

## 5. 2차 MVP 우선순위 요약

| 순위 | 항목 | 기대 역량 | 난이도 |
|---|---|---|---|
| 1 | **면접 시뮬레이션 Agent** | LangGraph StateGraph, 체크포인터, 스트리밍, Tool Calling | ★★★★ |
| 2 | **pgvector RAG — JD 중복 감지** | RAG 패턴, 벡터 DB, 임베딩 | ★★★ |
| 3 | **면접 질문 Agent 전환** | ReAct, Tool Calling, LangSmith | ★★★ |
| 4 | **사람인 파서 추가** | 크롤러 설계, BaseParser 확장 | ★★ |
| 5 | **에이전트 관측성 강화** | LangSmith 트레이싱, LLM-as-judge | ★★★ |

> **1순위 이유**: 면접 시뮬레이터는 LangGraph의 핵심 패턴(StateGraph + 메모리 + 조건부 엣지 + 스트리밍)을 한 번에 경험할 수 있고, 포트폴리오로도 직관적으로 어필이 강하다.
