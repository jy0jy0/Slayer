## 변경사항

**한 줄 요약:** 면접 질문 생성을 피드백 기반 반복 개선 루프로 전환 (pin, 메모, Refine, DB 저장, DOCX 내보내기)

### 무엇이 변경되었나요?
- 질문 pin 기능 추가 — Refine 시 선택한 질문을 원래 위치에 보존
- 질문별 메모 + 전체 피드백을 LLM 프롬프트에 반영하는 Refine 루프 구현
- 세션 내 이터레이션 이력 보관 (이전 결과 아코디언으로 확인 가능)
- 생성/재생성 결과를 `applications.interview_questions` JSONB에 자동 저장
- DOCX 다운로드 버튼 추가 (선택, 카테고리별 질문 + 예시 답변 포함)
- Reset 버튼 추가 — 질문 결과·이력·pin·메모 초기화 (JD/이력서/설정 유지)
- `OPENAI_API_KEY` 없을 때 Gemini 직접 호출로 JD-Resume 매칭 폴백 처리
- 카테고리 제외 로그에 누락 데이터 원인 추가

### 왜 이런 변경을 했나요?
기존 Interview Prep은 질문을 생성하면 그걸로 끝이어서 결과가 마음에 안 들어도 개선할 방법이 없었다. 마음에 드는 질문을 유지하면서 나머지만 다시 생성하거나, 구체적인 피드백을 반영해 방향을 바꾸는 인터랙션이 필요했다. 또한 생성된 질문이 DB에 저장되지 않아 이력 추적이 불가능했고, 오프라인 학습용 문서 내보내기도 없었다.

## 변경 유형

- [x] 새로운 기능
- [ ] 버그 수정
- [ ] 코드 리팩토링
- [ ] 문서 업데이트
- [ ] 설정/의존성 변경

## 관련 이슈/Discussion

- Related to #10

## 테스트

- [x] 로컬에서 동작 확인 완료
- [ ] 새 기능에 대한 테스트 추가 (해당 시)
- [ ] 기존 테스트 통과 확인

## 체크리스트

- [x] `slayer/schemas.py` 변경 시 팀원에게 공유
  - `RefinementFeedback` 모델 추가됨 (`free_text`, `question_notes`, `focus_categories`, `pinned_questions`)
- [ ] `.env.example` 업데이트 반영 (해당 시)
- [x] import 경로가 `from slayer.` 으로 통일
- [ ] 새 파일/디렉토리가 README에 반영
- [x] PR 제목이 변경 내용을 명확히 설명

## 참고사항

**변경된 파일:**
| 파일 | 변경 내용 |
|------|----------|
| `slayer/schemas.py` | `RefinementFeedback` 모델 추가 |
| `slayer/pipelines/interview_questions/generator.py` | `_build_feedback_section`, `_merge_questions`(위치 보존), `refine_interview_questions` 추가 |
| `slayer/pipelines/interview_questions/__init__.py` | `refine_interview_questions` 익스포트 추가 |
| `slayer/db/repository.py` | `save_interview_questions(jd, result)` 추가 |
| `slayer/llm.py` | `GeminiProvider` 추가, `get_default_provider()` 폴백 로직 추가 |
| `slayer/pipelines/jd_resume_matcher/matcher.py` | `_match_with_gemini()` 추가, OpenAI 키 없을 때 Gemini 분기 추가 |
| `slayer/ui/views/interview_prep.py` | UI 전면 재구성 (pin, 메모, Refine 폼, 이력, DB 저장, DOCX, Reset) |
| `docs/interview-prep-improvement-plan.md` | Before/After 비교, 사용 가이드, Pin/Reset 기능 문서 신규 작성 |

**Gemini 폴백 관련:**
`OPENAI_API_KEY` 미설정 환경에서도 `GOOGLE_API_KEY`만 있으면 JD-Resume 매칭이 동작한다. 단, OpenAI와 Gemini의 구현 방식이 다르다.

| | OpenAI | Gemini |
|---|---|---|
| 방식 | LangGraph ReAct 에이전트 (툴 호출 루프) | 3-step 순차 직접 호출 |
| 이유 | LangGraph 기본 지원 | `langchain-google-genai` 미설치로 LangGraph 연결 불가 → 직접 호출로 우회 |

두 방식 모두 동일한 `MatchingResult`를 반환한다. 추후 `langchain-google-genai` 추가 시 Gemini도 LangGraph 에이전트로 통일 가능하다.

**질문 노트 vs 전체 피드백:**
질문별 메모는 해당 질문을 어떻게 바꿔달라는 개별 지시, 전체 피드백은 재생성 전반의 방향 지시로 LLM 프롬프트 내 별도 섹션에 분리 주입된다. pin된 질문의 메모는 Refine 프롬프트에서 제외된다.
