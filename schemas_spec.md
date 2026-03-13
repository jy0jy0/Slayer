# Slayer 데이터 스키마 명세서

> **작성자**: 지호 (@jy0jy0)
> **최종 수정**: 2026-03-13
> **파일**: `schemas.py` (프로젝트 루트)

현지님이 제안한 대로 `schemas.py` 모듈에서 중앙 관리하고, 각 기능 모듈에서 import하여 사용합니다.

```python
from schemas import JDSchema, ParsedResume, MatchResult
```

Pydantic BaseModel 기반입니다 (openai SDK 의존성으로 이미 설치되어 있음).
`model_dump()`로 dict 변환이 되므로 TypedDict와 호환됩니다.

---

## 전체 데이터 흐름

```
[JD URL] ──→ JD 파싱 (현지) ──→ JDSchema ──────┐
                                                ├──→ MatchResult
[이력서 파일] ──→ 이력서 파싱 (예신) ──→ ParsedResume ┘
                                                │
[회사명] ──→ 기업 리서치 (지호) ──→ CompanyResearchOutput
                                                │
              ┌─────────────────────────────────┘
              ▼                                 ▼
    이력서 최적화 Agent (지호+현지)      자기소개서 생성 (지호)
              │                                 │
              ▼                                 ▼
    ResumeOptimizationOutput          CoverLetterOutput
```

### 모듈 간 계약

| 생산자 (Output) | 스키마 | 소비자 (Input) |
|-----------------|--------|----------------|
| 현지 — JD 파싱 | `JDSchema` | 매칭, 이력서 최적화, 자소서, 면접질문 |
| 예신 — 이력서 파싱 | `ParsedResume` | 매칭, 이력서 최적화, 자소서 |
| TBD — 매칭 | `MatchResult` | 이력서 최적화, 자소서 |
| 지호 — 기업 리서치 | `CompanyResearchOutput` | 자소서, 면접질문 |
| 지호+현지 — 이력서 최적화 | `ResumeOptimizationOutput` | 저장, 다운로드 |
| 지호 — 자소서 | `CoverLetterOutput` | 저장, 다운로드 |

---

## 1. JDSchema — 채용공고 구조화 데이터

**생산자**: 현지님 JD 파싱 Pipeline
**현지님 Discussion #6 스키마와 1:1 호환**

```python
class JDSchema(BaseModel):
    company: str              # "ABC 테크"
    title: str                # "Machine Learning Engineer"
    position: str             # "AI 서비스 개발"
    overview: JDOverview      # 아래 참조
    responsibilities: list[str]   # ["데이터 파이프라인 설계", "모델 배포"]
    requirements: JDRequirements  # 아래 참조
    skills: list[str]         # ["Python", "ML", "Docker"]
    benefits: list[str]       # ["자율 출퇴근", "교육비 지원"]
    process: list[str]        # ["서류전형", "코딩테스트", "면접"]
    notes: Optional[str]      # "국내/외 학회 참가 지원"
    url: Optional[str]        # "https://wanted.co.kr/xxx"
    platform: Optional[str]   # "wanted"
```

### JDOverview (채용 개요)

```python
class JDOverview(BaseModel):
    employment_type: Optional[str]  # "정규직"
    experience: Optional[str]       # "경력 3년 이상"
    education: Optional[str]        # "대졸 이상"
    salary: Optional[str]           # "면접 후 협의"
    location: Optional[str]         # "서울"
    deadline: Optional[str]         # "2025-12-31"
    headcount: Optional[str]        # "2명"
    work_hours: Optional[str]       # "주 5일"
```

### JDRequirements (자격 요건)

```python
class JDRequirements(BaseModel):
    required: list[str]     # ["Python", "ML 알고리즘 이해"]
    preferred: list[str]    # ["TensorFlow", "Docker"]
```

### 사용 예시

```python
from schemas import JDSchema

# 현지님 파서가 dict로 내보내면 → 바로 파싱 가능
jd = JDSchema(**parsed_dict)

# 역으로 dict 변환도 가능
jd_dict = jd.model_dump()
```

---

## 2. ParsedResume — 이력서 파싱 결과

**생산자**: 예신님 이력서 파싱 Pipeline
**목적**: PDF, DOCX, MD, JSON, TXT 등 다양한 포맷의 이력서를 통일된 구조로 변환

```python
class ParsedResume(BaseModel):
    personal_info: PersonalInfo
    summary: Optional[str]                      # 자기소개 요약문
    experiences: list[ExperienceItem]            # 경력 목록
    projects: list[ProjectItem]                  # 프로젝트 목록
    education: list[EducationItem]               # 학력 목록
    skills: list[str]                            # ["Java", "Spring Boot", "Kafka"]
    certifications: list[CertificationItem]      # 자격증 목록
    publications: list[PublicationItem]           # 논문/발표 목록
    total_years_experience: Optional[float]      # 총 경력 연수 (5.0)
    source_format: Optional[str]                 # "pdf", "docx", "md", "json", "txt"
```

### 하위 모델들

**PersonalInfo** — 인적사항

| 필드 | 타입 | 예시 |
|------|------|------|
| name | str | "김준혁" |
| email | str? | "junhyuk@example.com" |
| phone | str? | "010-0000-0001" |
| birth_year | int? | 1996 |
| links | list[str] | ["https://github.com/..."] |

**ExperienceItem** — 경력

| 필드 | 타입 | 예시 |
|------|------|------|
| company | str | "쿠팡" |
| position | str | "Senior Backend Engineer" |
| department | str? | "물류 플랫폼팀" |
| start_date | str | "2023-01" |
| end_date | str? | None (재직중이면 None) |
| is_current | bool | True |
| description | str? | "주문/배송 시스템 설계 및 운영" |
| achievements | list[str] | ["일평균 150만 건 주문 처리"] |

**ProjectItem** — 프로젝트

| 필드 | 타입 | 예시 |
|------|------|------|
| name | str | "결제 시스템 MSA 전환" |
| company | str? | "쿠팡" (개인 프로젝트면 None) |
| role | str? | "기술 리드" |
| start_date | str? | "2024-03" |
| end_date | str? | "2024-09" |
| description | str | "모놀리식 → MSA 전환" |
| tech_stack | list[str] | ["Java 17", "Spring Boot", "Kafka"] |
| achievements | list[str] | ["배포 주기 월 1회 → 주 3회"] |

**EducationItem** — 학력

| 필드 | 타입 | 예시 |
|------|------|------|
| school | str | "한양대학교" |
| major | str? | "컴퓨터소프트웨어학부" |
| degree | str? | "학사" / "석사" / "박사" |
| start_date | str? | "2015-03" |
| end_date | str? | "2021-02" |
| is_current | bool | False |

**CertificationItem** — 자격증

| 필드 | 타입 | 예시 |
|------|------|------|
| name | str | "AWS Solutions Architect" |
| issuer | str? | "Amazon Web Services" |
| date | str? | "2022-03" |

**PublicationItem** — 논문/발표

| 필드 | 타입 | 예시 |
|------|------|------|
| title | str | "Cross-lingual Transfer Learning..." |
| venue | str? | "ACL 2023 Findings" |
| date | str? | "2023" |
| url | str? | "https://arxiv.org/..." |

---

## 3. ResumeBlock — 이력서 블록 구조

이력서를 블록 단위로 분리하여 JD에 맞게 **재배치**할 수 있도록 하는 구조입니다.

```python
class BlockType(str, Enum):
    PERSONAL_INFO = "personal_info"
    SUMMARY       = "summary"
    EXPERIENCE    = "experience"
    PROJECT       = "project"
    EDUCATION     = "education"
    SKILLS        = "skills"
    CERTIFICATION = "certification"
    PUBLICATION   = "publication"
    AWARD         = "award"
    OTHER         = "other"

class ResumeBlock(BaseModel):
    block_type: BlockType
    order: int                          # 현재 순서 (0부터)
    content: dict                       # 블록 내용 (타입별로 다름)
    relevance_score: Optional[float]    # JD 대비 관련성 0.0~1.0
```

### 변환 함수

`parsed_resume_to_blocks(resume)` — ParsedResume → list[ResumeBlock] 변환

```python
# 예: 김준혁 이력서 → 11개 블록
[0] personal_info   ← 고정 (항상 최상단)
[1] experience      ← 쿠팡
[2] experience      ← 네이버
[3] project         ← 결제 MSA 전환
[4] project         ← 재고 관리
[5] project         ← 물류 최적화
[6] project         ← 인증 시스템
[7] education       ← 한양대
[8] skills          ← 기술스택 전체
[9] certification   ← 정보처리기사
[10] certification  ← AWS SAA
```

최적화 Agent가 JD를 보고 `order`를 바꾸거나 `content`를 보강합니다.

---

## 4. MatchResult — JD-이력서 매칭 결과

**담당자**: TBD (미팅에서 논의 필요)

```python
class MatchResult(BaseModel):
    ats_score: float              # 0~100 (종합 점수)
    score_breakdown: dict         # 카테고리별 점수
    matched_keywords: list[str]   # JD에 있고 이력서에도 있는 키워드
    missing_keywords: list[str]   # JD에 있는데 이력서에 없는 키워드
    strengths: list[str]          # 강점 목록
    weaknesses: list[str]         # 약점 목록
    gap_summary: str              # 갭 분석 요약
```

### ATS 점수 가중치 (RESUME_RESEARCH.md / JobPT 참고)

| 카테고리 | 가중치 | 설명 |
|----------|--------|------|
| ats_simulation | 0.30 | ATS 시뮬레이션 통과 여부 |
| keywords | 0.25 | 키워드 매칭률 |
| experience | 0.20 | 경력 적합도 |
| industry_specific | 0.15 | 산업/도메인 특화 |
| content | 0.05 | 내용 품질 |
| format | 0.03 | 이력서 형식 |
| errors | 0.02 | 오류/오타 |

### 예시

```json
{
  "ats_score": 65.0,
  "score_breakdown": {"keywords": 18, "experience": 16, "ats_simulation": 20, "industry_specific": 8, "content": 3},
  "matched_keywords": ["Python", "PyTorch", "ML"],
  "missing_keywords": ["Docker", "Kubernetes", "CI/CD"],
  "strengths": ["ML 경력 3년 이상 충족", "논문 실적 보유"],
  "weaknesses": ["DevOps 경험 부족", "팀 리딩 경험 미기재"],
  "gap_summary": "키워드 매칭률 72%. 인프라/배포 경험 보강 필요"
}
```

---

## 5. 이력서 최적화 Agent (Input/Output)

**담당**: 지호 + 현지

### Input

```python
class ResumeOptimizationInput(BaseModel):
    parsed_resume: ParsedResume     # 원본 이력서
    jd: JDSchema                    # 타겟 채용공고
    match_result: MatchResult       # 현재 매칭 점수
    target_ats_score: float = 80.0  # 목표 점수
    max_iterations: int = 3         # 최대 반복 횟수
```

### Output

```python
class ResumeOptimizationOutput(BaseModel):
    optimized_blocks: list[ResumeBlock]   # 최적화된 블록들 (순서 변경 + 내용 보강)
    final_ats_score: float                # 최종 ATS 점수
    score_improvement: float              # 개선 폭 (final - initial)
    changes: list[BlockChange]            # 변경 이력
    iterations_used: int                  # 실제 반복 횟수
    optimization_summary: str             # 요약
```

### BlockChange — 변경 이력

```python
class BlockChange(BaseModel):
    block_type: BlockType       # 어떤 블록인지
    original_order: int         # 원래 순서
    new_order: Optional[int]    # 변경된 순서
    change_type: str            # "reorder" | "enhance" | "add_keyword" | "quantify" | "remove"
    before: Optional[str]       # 변경 전
    after: Optional[str]        # 변경 후
    reason: str                 # 변경 사유
```

### Agent 루프 예시

```
1회차: ATS 65점 → 블록 재배치 (ML 프로젝트 상단 이동) → ATS 72점
2회차: ATS 72점 → 키워드 추가 (Docker, CI/CD 경험 보강) → ATS 80점
3회차: 목표 달성 → 종료
```

---

## 6. 자기소개서 생성 (Input/Output)

**담당**: 지호

### Input

```python
class CoverLetterInput(BaseModel):
    parsed_resume: ParsedResume          # 이력서
    jd: JDSchema                         # 채용공고
    company_research: CompanyResearchOutput  # 기업 리서치 결과
    match_result: MatchResult            # 매칭 결과 (강점/약점 참고)
```

### Output

```python
class CoverLetterOutput(BaseModel):
    cover_letter: str               # 자기소개서 본문
    key_points: list[str]           # 핵심 강조 포인트
    jd_keyword_coverage: float      # JD 키워드 반영률 0.0~1.0
    word_count: int                 # 글자 수
```

---

## 7. CompanyResearchOutput — 기업 리서치 결과

**담당**: 지호 (이미 구현 완료)
기존 `company_research/llm_client.py`의 JSON 출력을 Pydantic으로 정형화한 것입니다.

```python
class CompanyResearchOutput(BaseModel):
    company_name: str               # "삼성전자(주)"
    company_name_en: Optional[str]  # "SAMSUNG ELECTRONICS CO,.LTD"
    basic_info: BasicInfo           # 업종, 대표자, 설립일, 직원수, 주소, 상장정보
    financial_info: Optional[FinancialInfo]  # 매출, 영업이익, 자산, 부채비율
    recent_news: list[NewsItem]     # 최신 뉴스 목록
    summary: str                    # 구직자 관점 종합 요약 (200~400자)
    data_sources: list[str]         # ["naver_news", "corp_info", "financial_info"]
    researched_at: str              # ISO 8601 타임스탬프
```

---

## 논의 사항

### 1. JD-이력서 매칭 담당자 (TBD)
`MatchResult`를 누가 구현하는지 결정 필요. 이력서 최적화와 자기소개서 모두 이걸 입력으로 받음.

### 2. skills 중복 가능성
현지님 `JDSchema`에서 `skills`와 `requirements.required`가 겹칠 수 있음.
- `requirements.required` = 문장형 ("Python 3년 이상")
- `skills` = 태그형 ("Python")
- 매칭 시 어느 쪽을 기준으로 할지 합의 필요

### 3. ParsedResume.skills — flat vs categorized
현재 `skills: list[str]`로 flat하게 정의됨.
카테고리 분류 (languages, frameworks, tools 등)가 필요하면 예신님과 논의.

### 4. 날짜 포맷
스키마에서는 `str`로 느슨하게 잡아둠. 파싱 단계에서 `YYYY-MM` 포맷으로 정규화하는 게 이상적.

### 5. ID 필드
현재 스키마에 고유 식별자(id)가 없음. 버전 관리 + 이력 추적을 위해 추후 추가 고려.
- `JDSchema.id` — "wanted_12345"
- `ParsedResume.id` — UUID
- `MatchResult.jd_id`, `MatchResult.resume_id`
