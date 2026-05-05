"""면접 질문 생성 Pipeline.

담당: 현지
Input:  InterviewQuestionsInput (JDSchema + ParsedResume + CompanyResearchOutput + MatchResult)
Output: InterviewQuestionsOutput (questions + sample_answers + weak_areas)

카테고리:
    기술          — JD 스킬 × 이력서 기술스택 교차 검증
    경험          — 이력서 경력/프로젝트 구체적 확인
    상황/행동      — MatchResult gap 기반 (부족한 부분 공략)
    인성          — 범용 소프트스킬
    컬처핏        — 기업 리서치 + JD 조직문화 기반
    기업 이해도   — CompanyResearchOutput 뉴스/현황 기반
"""

from __future__ import annotations

import json
import logging

from slayer.pipelines.interview_questions.llm_client import GeminiProvider, LLMProvider
from slayer.schemas import (
    InterviewCategory,
    InterviewQuestion,
    InterviewQuestionsInput,
    InterviewQuestionsOutput,
    RefinementFeedback,
    SampleAnswer,
)

logger = logging.getLogger(__name__)

_ALL_CATEGORIES = list(InterviewCategory)

_CATEGORY_GUIDANCE: dict[InterviewCategory, str] = {
    InterviewCategory.TECHNICAL: (
        "JD의 required/preferred skills와 이력서의 skills를 교차 분석하여 "
        "기술 역량을 검증하는 질문을 생성합니다. "
        "특히 MatchResult의 missing_keywords에 있는 기술은 반드시 포함합니다."
    ),
    InterviewCategory.EXPERIENCE: (
        "이력서의 experiences와 projects 항목을 파고드는 질문을 생성합니다. "
        "특정 프로젝트/회사에서의 역할, 성과, 어려웠던 점을 구체적으로 묻습니다."
    ),
    InterviewCategory.SITUATIONAL: (
        "MatchResult의 weaknesses와 gap_summary를 기반으로, "
        "이력서에 없는 경험이나 부족한 역량에 대해 어떻게 대처할지 묻는 질문을 생성합니다. "
        "지원자 입장에서 가장 까다롭게 느낄 수 있는 질문들입니다."
    ),
    InterviewCategory.PERSONALITY: (
        "특정 경험/기술과 무관한 범용 소프트스킬 질문을 생성합니다. "
        "갈등 해결, 자기 인식, 성장 마인드셋 등을 탐색합니다."
    ),
    InterviewCategory.CULTURE_FIT: (
        "기업 리서치(업종, 규모, 최근 뉴스)와 JD의 조직문화 단서를 활용하여 "
        "해당 회사에 특화된 협업 방식/가치관 적합성을 묻는 질문을 생성합니다."
    ),
    InterviewCategory.COMPANY_KNOWLEDGE: (
        "CompanyResearchOutput의 recent_news, basic_info, summary를 활용하여 "
        "지원자가 해당 회사에 대해 얼마나 알고 있는지 확인하는 질문을 생성합니다."
    ),
}


_REQUIRES_COMPANY_RESEARCH = {
    InterviewCategory.CULTURE_FIT,
    InterviewCategory.COMPANY_KNOWLEDGE,
}
_REQUIRES_MATCH_RESULT = {
    InterviewCategory.SITUATIONAL,
}


def _resolve_categories(
    inp: InterviewQuestionsInput,
) -> tuple[list[InterviewCategory], list[InterviewCategory]]:
    """사용 가능한 데이터 기준으로 실제 생성할 카테고리를 결정한다.

    Returns:
        (생성할 카테고리 목록, 제외된 카테고리 목록)
    """
    categories = inp.categories or _ALL_CATEGORIES
    excluded: list[InterviewCategory] = []

    if inp.company_research is None:
        excluded += [c for c in categories if c in _REQUIRES_COMPANY_RESEARCH]
    if inp.match_result is None:
        excluded += [c for c in categories if c in _REQUIRES_MATCH_RESULT]

    if excluded:
        logger.warning(
            "데이터 부족으로 카테고리 제외: %s",
            ", ".join(c.value for c in excluded),
        )

    return [c for c in categories if c not in excluded], excluded


def _build_prompt(
    inp: InterviewQuestionsInput,
    categories: list[InterviewCategory],
    feedback: RefinementFeedback | None = None,
) -> str:
    n = inp.questions_per_category
    jd = inp.jd
    resume = inp.resume

    experience_summary = "\n".join(
        f"- {e.company} / {e.position} ({e.start_date} ~ {e.end_date or '현재'}): "
        f"{', '.join(e.achievements[:2]) if e.achievements else e.description or ''}"
        for e in resume.experiences
    )
    project_summary = "\n".join(
        f"- {p.name} ({', '.join(p.tech_stack)}): {p.description[:80] if p.description else ''}"
        for p in resume.projects
    )

    # 기업 리서치 섹션 — 데이터 없으면 생략
    if inp.company_research is not None:
        research = inp.company_research
        news_summary = "\n".join(
            f"- {item.title} ({item.published_date or '날짜 미상'})"
            for item in research.recent_news[:5]
        )
        company_research_section = f"""
## 기업 리서치
- 업종: {research.basic_info.industry or '미상'}
- 회사 규모: {research.basic_info.employee_count or '미상'}명
- 요약: {research.summary[:300] if research.summary else '정보 없음'}
- 최근 뉴스:
{news_summary or '없음'}
"""
    else:
        company_research_section = "\n## 기업 리서치\n- 정보 없음 (컬처핏·기업이해도 카테고리 제외됨)\n"

    # 매칭 분석 섹션 — 데이터 없으면 생략
    if inp.match_result is not None:
        match = inp.match_result
        match_section = f"""
## JD-이력서 매칭 분석
- ATS 점수: {match.ats_score:.1f}점
- 매칭 키워드: {', '.join(match.matched_keywords[:10])}
- 누락 키워드: {', '.join(match.missing_keywords[:10])}
- 강점: {', '.join(match.strengths[:3])}
- 약점: {', '.join(match.weaknesses[:3])}
- 갭 요약: {match.gap_summary}
"""
        weak_areas_instruction = "MatchResult 약점 기반으로 우선적으로 대비해야 할 영역 3~5개"
    else:
        match_section = "\n## JD-이력서 매칭 분석\n- 정보 없음 (상황/행동 카테고리 제외됨)\n"
        weak_areas_instruction = "JD 요건과 이력서 비교 기반으로 우선적으로 대비해야 할 영역 3~5개"

    category_instructions = "\n".join(
        f"### {cat.value}\n{_CATEGORY_GUIDANCE[cat]}"
        for cat in categories
    )

    return f"""당신은 채용 면접 전문가입니다.
아래 정보를 바탕으로 지원자가 면접을 대비할 수 있도록 카테고리별 면접 질문과 예시 답변을 생성해주세요.

## 채용공고 정보
- 회사: {jd.company}
- 포지션: {jd.position}
- 주요 업무: {', '.join(jd.responsibilities[:5])}
- 필수 요건: {', '.join(jd.requirements.required[:5])}
- 우대 사항: {', '.join(jd.requirements.preferred[:3])}
- 요구 스킬: {', '.join(jd.skills[:10])}

## 지원자 이력서 요약
- 이름: {resume.personal_info.name}
- 총 경력: {resume.total_years_experience or '미상'}년
- 보유 스킬: {', '.join(resume.skills[:15])}
- 경력:
{experience_summary or '없음'}
- 프로젝트:
{project_summary or '없음'}
{company_research_section}{match_section}
## 생성 지침
각 카테고리별로 정확히 {n}개의 질문을 생성합니다.

{category_instructions}

## 출력 형식 (JSON)
아래 구조를 정확히 따르세요:

{{
  "questions": [
    {{
      "category": "카테고리명 ({"|".join(c.value for c in categories)} 중 하나)",
      "question": "면접 질문",
      "intent": "면접관이 이 질문을 하는 이유 (1~2문장)",
      "tip": "답변 시 유의할 점 또는 전략 (1~2문장)",
      "source": "생성 근거 (예: 'missing_keyword: Blender', 'experience: ABC 프로젝트', 'company_news: 100만 사용자 돌파')"
    }}
  ],
  "sample_answers": [
    {{
      "question": "위 questions 중 카테고리별 1개씩 선택한 질문 (총 {len(categories)}개)",
      "answer": "STAR 기법(상황-과제-행동-결과)을 활용한 예시 답변. 이력서 내용을 구체적으로 활용할 것."
    }}
  ],
  "weak_areas": ["{weak_areas_instruction}"]
}}

생성할 카테고리: {', '.join(cat.value for cat in categories)}
{_build_feedback_section(feedback) if feedback else ""}"""


def _build_feedback_section(feedback: RefinementFeedback) -> str:
    """피드백 섹션 문자열 생성 — _build_prompt 끝에 삽입된다."""
    pinned_lines = "\n".join(
        f"- [{q.category.value if hasattr(q.category, 'value') else q.category}] {q.question}"
        for q in feedback.pinned_questions
    )
    focus_str = (
        ", ".join(c.value for c in feedback.focus_categories)
        if feedback.focus_categories
        else "없음 (전체 균등 생성)"
    )
    return f"""

## 재생성 피드백 (이전 버전 개선 요청)
사용자가 이전 결과에 대해 다음 피드백을 제공했습니다. 반드시 반영하세요.

피드백: {feedback.free_text or "(없음)"}
집중 카테고리: {focus_str}

이미 확정된 질문 (중복 생성 금지 — 아래 질문과 동일하거나 유사한 질문은 생성하지 마세요):
{pinned_lines or "없음"}
"""


def _merge_questions(
    pinned: list[InterviewQuestion],
    new_questions: list[InterviewQuestion],
    questions_per_category: int,
) -> list[InterviewQuestion]:
    """고정 질문 + 새 질문을 카테고리별로 병합한다.

    - pinned 질문은 항상 유지 (questions_per_category 초과해도 보존)
    - 남은 슬롯을 new_questions로 채움
    """
    from collections import defaultdict

    pinned_by_cat: dict[str, list[InterviewQuestion]] = defaultdict(list)
    for q in pinned:
        cat = q.category.value if hasattr(q.category, "value") else str(q.category)
        pinned_by_cat[cat].append(q)

    new_by_cat: dict[str, list[InterviewQuestion]] = defaultdict(list)
    for q in new_questions:
        cat = q.category.value if hasattr(q.category, "value") else str(q.category)
        new_by_cat[cat].append(q)

    result: list[InterviewQuestion] = []
    all_cats = list(pinned_by_cat.keys()) + [c for c in new_by_cat if c not in pinned_by_cat]

    for cat in all_cats:
        p_qs = pinned_by_cat[cat]
        n_qs = new_by_cat[cat]
        slots = max(questions_per_category, len(p_qs))
        combined = p_qs + n_qs[: max(0, slots - len(p_qs))]
        result.extend(combined)

    return result


def generate_interview_questions(
    inp: InterviewQuestionsInput,
    provider: LLMProvider | None = None,
) -> InterviewQuestionsOutput:
    """면접 질문을 생성합니다.

    Args:
        inp: JD, 이력서, 기업 리서치, 매칭 결과를 담은 입력 객체
        provider: LLM Provider (기본값: GeminiProvider)

    Returns:
        카테고리별 면접 질문, 예시 답변, 우선 대비 영역
    """
    if provider is None:
        provider = GeminiProvider()

    categories, excluded = _resolve_categories(inp)
    logger.info(
        "면접 질문 생성 시작 — %s / %s | 카테고리: %s | 카테고리당 %d개",
        inp.jd.company,
        inp.jd.position,
        ", ".join(c.value for c in categories),
        inp.questions_per_category,
    )

    logger.info("LLM API 호출 중... (%s)", type(provider).__name__)
    raw = provider.generate_json(_build_prompt(inp, categories))
    logger.info("응답 수신 완료, 파싱 중...")

    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        logger.error("LLM 응답 JSON 파싱 실패. raw response: %s", raw)
        raise

    questions = [InterviewQuestion(**q) for q in data.get("questions", [])]
    sample_answers = [SampleAnswer(**a) for a in data.get("sample_answers", [])]
    weak_areas: list[str] = data.get("weak_areas", [])

    logger.info(
        "생성 완료 — 질문 %d개 / 예시 답변 %d개 / 우선 대비 영역 %d개",
        len(questions),
        len(sample_answers),
        len(weak_areas),
    )

    return InterviewQuestionsOutput(
        questions=questions,
        sample_answers=sample_answers,
        weak_areas=weak_areas,
        excluded_categories=[c.value for c in excluded],
    )


def refine_interview_questions(
    inp: InterviewQuestionsInput,
    feedback: RefinementFeedback,
    provider: LLMProvider | None = None,
) -> InterviewQuestionsOutput:
    """피드백 기반 면접 질문 재생성.

    - feedback.pinned_questions: 보존할 질문 (LLM 재생성에서 제외 지시 후 결과에 병합)
    - feedback.free_text: 자유 피드백 → 프롬프트에 직접 삽입
    - feedback.focus_categories: 집중 카테고리 → 해당 카테고리 위주로 생성
    """
    if provider is None:
        provider = GeminiProvider()

    inp_for_refinement = (
        inp.model_copy(update={"categories": feedback.focus_categories})
        if feedback.focus_categories
        else inp
    )

    categories, excluded = _resolve_categories(inp_for_refinement)
    logger.info(
        "면접 질문 재생성 시작 — %s / %s | 카테고리: %s | pinned: %d개",
        inp.jd.company,
        inp.jd.position,
        ", ".join(c.value for c in categories),
        len(feedback.pinned_questions),
    )

    prompt = _build_prompt(inp_for_refinement, categories, feedback=feedback)
    raw = provider.generate_json(prompt)
    logger.info("재생성 응답 수신 완료, 파싱 중...")

    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        logger.error("재생성 LLM 응답 JSON 파싱 실패. raw response: %s", raw)
        raise

    new_questions = [InterviewQuestion(**q) for q in data.get("questions", [])]
    sample_answers = [SampleAnswer(**a) for a in data.get("sample_answers", [])]
    weak_areas: list[str] = data.get("weak_areas", [])

    merged = _merge_questions(feedback.pinned_questions, new_questions, inp.questions_per_category)

    logger.info(
        "재생성 완료 — 병합 질문 %d개 (pinned %d + new %d) / 예시 답변 %d개",
        len(merged),
        len(feedback.pinned_questions),
        len(new_questions),
        len(sample_answers),
    )

    return InterviewQuestionsOutput(
        questions=merged,
        sample_answers=sample_answers,
        weak_areas=weak_areas,
        excluded_categories=[c.value for c in excluded],
    )
