# Interview Prep — 개선 계획

## 왜 이 작업을 하는가

현재 `interview_prep.py`는 질문을 한 번 생성하고 보여주는 것에 그친다.
- 결과가 마음에 안 들어도 피드백을 줄 방법이 없다
- 마음에 드는 질문을 유지하면서 나머지만 개선할 수 없다
- 생성 결과가 DB에 저장되지 않는다 (로그만 남음)
- 오프라인으로 공부할 수 있는 문서 내보내기가 없다

---

## Before / After 비교

### 화면 노출 항목

| 필드 | Before | After | 이유 |
|------|--------|-------|------|
| `question` | bold 텍스트, 항상 표시 | 동일 + pin 버튼 추가 | 핵심 컨텐츠 |
| `tip` | 파란 박스, 항상 표시 | 동일 | 가장 actionable |
| `source` | 작은 배지, 항상 표시 | 동일 | 작아서 방해 없음 |
| `intent` | `st.caption`으로 항상 표시 | **기본 접힘, 토글로 열람** | 항상 보이면 읽기 흐름 방해 |
| per-question 메모 | 없음 | **텍스트 입력 추가** | 개선 방향 메모 용도 |
| pin 버튼 | 없음 | **질문 옆에 📌 버튼** | Refine 시 해당 질문 유지 |

### 전체 페이지 구조

```
Before:
┌─────────────────────────────────────┐
│ 상태 표시 (JD / Resume / Research / Match) │
│ [슬라이더] questions per category     │
│ [Generate 버튼]                       │
├─────────────────────────────────────┤
│ 카테고리별 질문 (question + intent + tip + source) │
│ 샘플 답변                             │
│ 우선 대비 영역                         │
│ Raw JSON expander                    │
└─────────────────────────────────────┘

After:
┌─────────────────────────────────────┐
│ 상태 표시 (JD / Resume / Research / Match) │
│ [슬라이더]   [Generate 버튼] [Reset]  │
├─────────────────────────────────────┤
│ [이터레이션 배너] Iteration N | Questions X | Pinned Y │
│                                     [⬇ DOCX (선택)] │
├─────────────────────────────────────┤
│ 카테고리별 질문                        │
│   Q1. 질문텍스트            [📌 pin] │
│   💡 Tip: ...                        │
│   [Show intent 토글] [Source 배지]   │
│   [개선 방향 메모 입력]               │
│   Q2. ...                            │
├─────────────────────────────────────┤
│ ── Refine Questions ──               │
│ [피드백 텍스트 입력]                   │
│ [집중 카테고리 멀티셀렉트]             │
│ 📌 N question(s) pinned             │
│ [🔄 Refine Questions 버튼]           │
├─────────────────────────────────────┤
│ 샘플 답변 (expander)                  │
│ 우선 대비 영역                         │
├─────────────────────────────────────┤
│ ▼ Previous Iterations (이력, 접힘)   │
│ Raw JSON expander                    │
└─────────────────────────────────────┘
```

### 데이터 흐름

| 항목 | Before | After |
|------|--------|-------|
| DB 저장 | agent_log만 (질문 내용 없음) | **`applications.interview_questions` JSONB에 전체 결과 저장** (기본) |
| 내보내기 | 없음 (Raw JSON 보기만) | **DOCX 다운로드 버튼** (선택, 사용자가 원할 때) |
| 이력 | 없음 | **세션 내 이전 이터레이션 보관** |

---

## 변경할 파일

| 파일 | 변경 유형 | 내용 |
|------|----------|------|
| `slayer/schemas.py` | 추가 | `RefinementFeedback` 모델 |
| `slayer/pipelines/interview_questions/generator.py` | 추가 | `_build_prompt` 피드백 주입, `_merge_questions`, `refine_interview_questions` |
| `slayer/pipelines/interview_questions/__init__.py` | 추가 | `refine_interview_questions` 익스포트 |
| `slayer/db/repository.py` | 추가 | `save_interview_questions(jd, result)` |
| `slayer/ui/views/interview_prep.py` | 수정 | 결과 표시부 재구성 + Refine 폼 + DB 저장 + DOCX 다운로드 |

---

## 상세 구현 계획

### 1. `slayer/schemas.py` — RefinementFeedback 추가

`InterviewQuestionsOutput` (line 582) 바로 뒤에 추가:

```python
class RefinementFeedback(BaseModel):
    """피드백 기반 재생성 입력."""
    free_text: str = ""
    focus_categories: list[InterviewCategory] = Field(default_factory=list)
    pinned_questions: list[InterviewQuestion] = Field(default_factory=list)
```

---

### 2. `slayer/pipelines/interview_questions/generator.py`

#### 2a. `_build_prompt` 시그니처 변경 (하위 호환)

```python
def _build_prompt(
    inp: InterviewQuestionsInput,
    categories: list[InterviewCategory],
    feedback: "RefinementFeedback | None" = None,
) -> str:
```

프롬프트 끝(JSON 출력 형식 앞)에 조건부 섹션 삽입:

```
## 재생성 피드백
피드백: {feedback.free_text}
집중 카테고리: {카테고리 목록 또는 "없음 (전체 균등 생성)"}
이미 확정된 질문 (중복 생성 금지):
- [기술] 질문 텍스트
...
위 확정 질문과 중복/유사한 질문은 생성하지 마세요.
```

#### 2b. `_merge_questions` 헬퍼

- pinned 질문을 카테고리별로 우선 배치
- 남은 슬롯을 새 질문으로 채움
- pinned 질문은 `questions_per_category` 초과해도 항상 유지

```python
def _merge_questions(
    pinned: list[InterviewQuestion],
    new_questions: list[InterviewQuestion],
    questions_per_category: int,
) -> list[InterviewQuestion]:
```

#### 2c. `refine_interview_questions` 함수

```python
def refine_interview_questions(
    inp: InterviewQuestionsInput,
    feedback: RefinementFeedback,
    provider: LLMProvider | None = None,
) -> InterviewQuestionsOutput:
    # focus_categories 있으면 inp.categories를 override
    # _build_prompt(inp, categories, feedback=feedback) 호출
    # LLM 응답 파싱 후 _merge_questions로 pinned + new 병합
    # InterviewQuestionsOutput 반환
```

---

### 3. `slayer/db/repository.py` — DB 저장

`applications.interview_questions` JSONB 컬럼이 `models.py:178`에 이미 존재.
저장 로직만 없는 상태이므로 `save_interview_questions` 함수 추가.

#### 동작 순서

1. JD의 company name으로 `Company` 행 조회
2. 해당 company_id를 가진 가장 최신 `Application` 행 조회
3. 찾으면 → `interview_questions` 컬럼 업데이트
4. 못 찾으면 → 최소 필드로 새 `Application` 행 생성

```python
@_safe_db_op
def save_interview_questions(jd, result) -> Any:
    from slayer.db.models import Application, Company
    with get_session() as session:
        company_id = None
        if jd.company:
            company = session.query(Company).filter_by(name=jd.company).first()
            if company:
                company_id = company.id

        app = None
        if company_id:
            app = (
                session.query(Application)
                .filter_by(company_id=company_id)
                .order_by(Application.created_at.desc())
                .first()
            )

        if app:
            app.interview_questions = result.model_dump()
        else:
            app = Application(
                id=uuid.uuid4(),
                user_id=uuid.UUID('00000000-0000-0000-0000-000000000000'),
                company_id=company_id or uuid.UUID('00000000-0000-0000-0000-000000000000'),
                status='reviewing',
                interview_questions=result.model_dump(),
            )
            session.add(app)
        return app
```

#### UI 호출 시점

질문 생성/재생성 성공 직후, `save_agent_log`와 동일한 non-blocking 패턴:

```python
try:
    from slayer.db.repository import save_interview_questions
    save_interview_questions(jd, result)
except Exception as e:
    logger.warning("DB save failed: %s", e)
```

---

### 4. `slayer/ui/views/interview_prep.py` — UI 재구성

#### 4a. 세션 상태 키

```python
st.session_state["interview_pinned"]   # dict[question_text, bool]
st.session_state["interview_notes"]    # dict[question_text, str]
st.session_state["interview_history"]  # list[InterviewQuestionsOutput]
```

pin/note는 질문 텍스트를 키로 사용 → 이터레이션 간 순서 변경에도 안전

#### 4b. Generate + Reset 버튼

```python
col_gen, col_reset = st.columns([3, 1])
with col_gen:
    run_btn = st.button("🎯 Generate Interview Questions", type="primary", use_container_width=True)
with col_reset:
    reset_btn = st.button("🗑 Reset", use_container_width=True)
    # → interview_pinned, interview_notes, interview_history, interview_result 전부 초기화
```

#### 4c. 이터레이션 배너 + DOCX 다운로드 (선택)

```python
col_banner, col_dl = st.columns([4, 1])
with col_banner:
    # Iteration N | Questions X | Pinned Y — #1a2744 배경
with col_dl:
    st.download_button("⬇ DOCX", data=_build_docx(result, jd),
                       file_name=f"{jd.company}_{jd.position}_면접질문.docx",
                       mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document")
```

#### 4d. 질문 카드 (per-question)

```python
col_q, col_pin = st.columns([11, 1])
with col_q:
    st.markdown(f"**Q{i}. {q.question}** {'📌' if pinned else ''}")
with col_pin:
    if st.button("📌" if not pinned else "✅", key=f"pin_{q_key}"):
        st.session_state["interview_pinned"][q.question] = not pinned
        st.rerun()

# tip — 항상 표시
st.html(f'<div style="background:#1a2744; ...">💡 {q.tip}</div>')

# intent — 기본 접힘
if st.toggle("Show intent", key=f"intent_{q_key}", value=False):
    st.caption(f"Intent: {q.intent}")

# source badge
st.html(f'<span style="...">Source: {q.source}</span>')

# 개선 방향 메모
note = st.text_input("개선 방향 (optional)", value=..., key=f"note_{q_key}",
                     placeholder="e.g. 더 구체적인 기술 질문으로")
st.session_state["interview_notes"][q.question] = note
```

#### 4e. Refine 폼 (`st.form`)

```python
with st.form("feedback_form"):
    feedback_text = st.text_area("피드백", placeholder="e.g. 기술 질문을 더 심화해줘...")
    focus_cats = st.multiselect("집중 카테고리 (선택 없으면 전체)", options=[...])
    # pinned 수 표시
    st.form_submit_button("🔄 Refine Questions", type="primary")
```

`st.form` 사용 이유: multiselect 변경이 text_area 입력 중 rerun을 트리거하지 않도록

#### 4f. DOCX 내보내기 헬퍼

```python
def _build_docx(result, jd) -> bytes:
    from docx import Document
    from io import BytesIO
    import datetime

    doc = Document()
    doc.add_heading(f"{jd.company} — {jd.position} 면접 준비 자료", 0)
    doc.add_paragraph(f"생성일: {datetime.date.today()}")

    if result.weak_areas:
        doc.add_heading("우선 대비 영역", level=1)
        for area in result.weak_areas:
            doc.add_paragraph(area, style="List Bullet")

    # 카테고리별 질문
    for cat, questions in by_category.items():
        doc.add_heading(f"{display_label} ({cat})", level=1)
        for i, q in enumerate(questions, 1):
            p = doc.add_paragraph()
            p.add_run(f"Q{i}. {q.question}").bold = True
            doc.add_paragraph(f"💡 Tip: {q.tip}")

    # 예시 답변
    if result.sample_answers:
        doc.add_heading("예시 답변", level=1)
        for sa in result.sample_answers:
            p = doc.add_paragraph()
            p.add_run(f"Q. {sa.question}").bold = True
            doc.add_paragraph(f"A. {sa.answer}")

    buf = BytesIO()
    doc.save(buf)
    return buf.getvalue()
```

#### 4g. 이전 이터레이션 이력

피드백 폼 아래에 접힌 accordion (최신순):

```python
for idx, old_result in enumerate(reversed(history), 1):
    with st.expander(f"Iteration {iter_num} — {len(old_result.questions)} questions", expanded=False):
        for old_q in old_result.questions:
            st.markdown(f"- **[{cat}]** {old_q.question}")
```

---

## 주의 사항

- **pin 버튼 클릭 시 `st.rerun()` 필요**: form 밖에 있어서 rerun으로 아이콘 갱신
- **note 저장 타이밍**: rerun 전에 `session_state["interview_notes"]`에 저장해야 소실 안 됨
- **focus_categories 유효성 검사**: 컬처핏/기업이해도는 company_research 없으면 제외됨 → UI에서 미리 경고
- **DB 저장은 기본**: 생성/재생성 성공 시 항상 호출, DOCX는 사용자가 버튼 클릭 시에만

---

## 검증 방법

1. `streamlit run slayer/ui/app.py`
2. JD Parser → JD-Resume Match 순으로 데이터 로드
3. Interview Prep에서 질문 생성
4. 질문 pin → Refine → pin된 질문이 유지되는지 확인
5. 피드백 입력 후 재생성 → 방향 반영 여부 확인
6. 이전 이터레이션 아코디언에서 이력 확인
7. DOCX 다운로드 버튼 클릭 → 파일 열어서 구조 확인
8. DB 연결 시 `applications.interview_questions` 컬럼에 JSON 저장 여부 확인
9. Reset 버튼으로 초기화 확인
