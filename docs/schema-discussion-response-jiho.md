# Schema 논의 응답 — 지호 (@jy0jy0)

작성일: 2026-04-11
참조 문서: `schema-discussion.md` (현지 @shinhyunji36 공유)
관련 PR: #19 (feat/apply-pipeline, @yesinkim) — OPEN

---

## 1. 전체 평가

논의 문서의 방향성에 전반적으로 **동의**한다. 특히 Q3("우리 서비스 = 개인 구직 아카이브") 정의는 지금까지 팀 내 암묵적 합의를 처음으로 명확히 언어화한 것이라고 본다. 이 정의가 확정되면 이후 스키마 논의가 훨씬 빠르게 수렴할 수 있다.

다만 본 응답은 **코드 변경을 동반하지 않는다**. `slayer/schemas.py`와 `slayer/db/models.py` 수정은 지호의 담당 범위(Agent/LLM/UI 레이어)를 벗어나므로, 이 문서는 "지호 관점 의견 + 검증된 DB 상태 공유 + 4/12 미팅 의사결정 지원" 용도로만 사용한다.

---

## 2. Q3 서비스 정의 — 동의

**"Slayer = 개인 구직 아카이브"** 정의에 동의.

**근거**: 현재 Streamlit UI의 6개 탭은 이미 "한 사람이 한 공고에 지원하는 흐름"을 전제로 설계되어 있다:

```
URL 입력 → JD 파싱 → 이력서 업로드 → 매칭 → 최적화 → 자기소개서 → 면접 준비
```

이 흐름 어디에도 "여러 사용자가 동일 JD를 공유한다"는 전제가 없다. 공용 job_postings 모델은 잡코리아/원티드 같은 공개 플랫폼에 적합하지만 우리 UX와는 어긋난다. 따라서 **개인 아카이브 전제로 스키마를 재정렬하는 것이 자연스럽다**.

---

## 3. Q7 applications 활용안 — 동의

JD 파싱 시점에 `applications` row를 `status='scrapped'`로 먼저 생성하고, 이후 매칭/최적화/자소서는 모두 `application_id`를 참조하는 구조에 동의.

**이유**:
- 현재는 각 단계(매칭, 최적화, 자소서)가 서로 "같은 application에 속하는 작업"이라는 연결 정보를 공유하지 못한다.
- 미래에 "이 지원에 대해 내가 한 모든 작업 이력"을 한 번에 조회하려면 `application_id`를 중심축으로 두어야 한다.
- PR #19의 `apply()` 파이프라인이 이미 유사한 모양(Company UPSERT → Application INSERT → Status History)을 갖추고 있어, 이 플로우를 JD 파싱 시점까지 앞당기면 자연스럽게 연결된다.

---

## 4. Q9 우선순위에 대한 지호 관점

본인 체감 우선순위 (높은 것부터):

| 순위 | 항목 | 이유 |
|---|---|---|
| 1 | `save_match_result()` silent fail **가시화** | 현재 매칭 결과가 전혀 쌓이지 않는데 아무도 모르는 상태다. 최소한 에러 로깅 상향(warning → error)이라도 먼저. |
| 2 | JD 파싱 시점 → application 생성 플로우 구현 | 이게 되면 applications 테이블에 실제 row가 쌓이기 시작한다. |
| 3 | `applications.company_id` nullable 여부 최종 결정 | PR #19가 임시로 placeholder company를 UPSERT하는 방식으로 우회 중. 이 우회가 장기적 정답인지 논의 필요. |
| 4 | `job_postings`에 `user_id` 추가 여부 | row 0개 상태에서 스키마 변경은 이르다. applications flow가 먼저 돌아간 뒤 재평가하자. |

**요약**: 스키마 표준화 자체보다 **"실제로 row가 쌓이게 만드는 게" 먼저**다. 쌓이고 나서 관찰하면 무엇을 바꿔야 할지 더 명확해진다.

---

## 5. 실제 DB 상태 보고 (지호 검증, 2026-04-11)

Supabase에 직접 쿼리한 결과:

| 테이블 | Row 수 | 비고 |
|---|---|---|
| `users` | 2 | 예신, manage.slayer |
| `companies` | 1 | `save_company()`는 실제로 INSERT 성공 중 |
| `job_postings` | 16 | 현지님 JD 파서 UI 통합 이후 실제 파싱 결과가 쌓이기 시작 |
| `agent_logs` | 3 | 지호 agent 실행 로그 일부 저장됨 |
| `applications` | **0** | ⚠️ FK 위반으로 전부 silent fail |

**placeholder UUID `00000000-0000-0000-0000-000000000000`** 는 `users` 테이블에 **존재하지 않는다**. 따라서 `save_match_result()`는 현재 다음 플로우로 동작한다:

1. `@_safe_db_op` 데코레이터 진입
2. `Application(user_id=placeholder, ...)` INSERT 시도
3. Postgres FK 제약 위반
4. SQLAlchemy 예외 발생
5. `@_safe_db_op`가 예외를 `logger.warning`으로 삼키고 `None` 반환
6. 호출자는 "저장됐겠지"라고 생각하고 진행

→ 매칭 기능을 몇 번을 돌려도 `applications` 테이블에는 아무 것도 쌓이지 않는 상태가 **PR #17 머지 이후 지금까지 계속되고 있다**.

---

## 6. PR #19과의 상호작용

예신님 PR #19가 이 논의의 일부를 이미 해결하는 중임을 확인했다:

| 논의 항목 | PR #19 해결 여부 |
|---|---|
| `save_application()`이 real `user_id`를 수령 | ✅ 해결 (request 파라미터로 받음) |
| `upsert_company_by_name()`로 company placeholder 자동 생성 | ✅ 해결 (없으면 minimal Company row 생성) |
| Apply 파이프라인이 `StatusHistory`까지 함께 기록 | ✅ 해결 |
| Gmail/Calendar 이벤트가 real `user_id`로 저장 | ✅ 해결 |
| `save_match_result()`의 fake UUID 제거 | ❌ **미해결** — PR #19는 이 함수를 건드리지 않는다 |
| `applications.company_id` nullable 전환 | ❌ 미해결 — 우회로 대체 중 |
| `save_company()` / `save_agent_log()`의 `user_id` 추적 | ❌ 미해결 |

→ **결론**: 논의 문서의 상당 부분은 PR #19 머지로 자동 해소되지만, **`save_match_result()` silent fail만은 독립적인 결정이 필요**하다.

---

## 7. 역할 분담 제안 (지호 직접 수정 없음)

지호는 다음 항목을 **직접 수정하지 않는다** (담당 범위 밖):

- `slayer/schemas.py`, `slayer/db/models.py`, `alembic migrations/`
- `save_match_result()`의 FK 수정 (DB 스키마와 연결되므로 예신님 영역에 근접)
- Apply/Gmail/Resume parser 파이프라인 (PR #19 영역)

지호가 담당하는 영역:
- Agent / LLM / UI 레이어 하드닝 (현재 `fix/agent-hardening-v2` 브랜치에서 진행)
- 본 응답 문서 (팀 공유)
- 4/12 미팅 의사결정 지원

제안:
- **스키마 표준화** → **예신 or 현지** 중 1명 담당 (PR #19 머지 이후)
- **`save_match_result()` FK 수정** → **예신** (repository.py 오너십 연속성)

---

## 8. 4/12 오프라인 미팅 의사결정 포인트

다음 5가지를 미팅에서 확정하자:

1. **스키마 표준화 담당자 확정** (예신 / 현지 중 1명)
2. **`save_match_result()` FK 수정 시점** (PR #19 머지 전 / 후 / 별도 PR)
3. **`applications.status` enum 최종 정의**
   - 현재 모델은 `scrapped / reviewing / applied / in_progress / final_pass / rejected / withdrawn`
   - PR #19의 플로우와 정합성 재검증 필요
4. **Company placeholder 전략**
   - PR #19는 `upsert_company_by_name()`으로 최소 정보 row 생성 후 `company_id` FK를 채운다
   - 이 방식을 장기 기본값으로 유지할지, 아니면 `company_id`를 nullable로 완전 전환할지
5. **본 논의 결론을 어떤 PR 단위로 반영할지**
   - 단일 거대 PR vs 항목별 분할 PR

---

## 9. 부록 — `save_match_result()` silent fail 재현 방법

누구든 로컬에서 다음으로 재현 가능:

```python
from slayer.db.session import get_session, is_db_available
from slayer.db.repository import save_match_result
from slayer.pipelines.jd_resume_matcher.matcher import create_mock_match_result

assert is_db_available(), "DATABASE_URL 필요"

result = save_match_result(
    jd_json='{"company": "카카오", "title": "백엔드"}',
    resume_json='{"personal_info": {"name": "테스트"}}',
    match_result=create_mock_match_result(),
)
print(result)  # → None (silent fail)

# Supabase에서 직접 확인
from sqlalchemy import text
with get_session() as session:
    count = session.execute(text("SELECT count(*) FROM applications")).scalar()
    print(count)  # → 0 (여전히 0)
```

---

_질문·반박 환영. 슬랙 또는 4/12 오프라인 미팅에서._
