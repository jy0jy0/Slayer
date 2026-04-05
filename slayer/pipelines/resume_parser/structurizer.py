"""추출된 텍스트 → LLM structured output → ParsedResume.

GOOGLE_API_KEY → Gemini 2.5 Flash
OPENAI_API_KEY → GPT-4o-mini (fallback)

공유 클라이언트: slayer.pipelines.resume_parser.llm_client
"""

from __future__ import annotations

from datetime import date

from slayer.pipelines.resume_parser.file_detector import ResumeLLMError
from slayer.schemas import ExperienceItem, ParsedResume
from slayer.pipelines.resume_parser.llm_client import generate_structured

_SYSTEM_PROMPT = """\
You are an expert resume parser. Extract structured information from the resume text below.

Rules:
- Parse both Korean and English resumes
- Dates: use "YYYY-MM" format (e.g. "2022-03"). If only year is given, use "YYYY-01"
- skills: lowercase, normalized (e.g. "python", "react", "aws")
- is_current: true if the person is currently in this role/school
- If information is missing, use null for optional fields and empty lists for list fields
- Do NOT fabricate information that is not in the resume
"""


def _calc_experience_years(experiences: list[ExperienceItem]) -> float:
    """경력 항목에서 총 경력 연수를 계산 (인턴 제외).

    - is_current=True이면 오늘 날짜까지 계산
    - position에 '인턴'이 포함된 항목 제외
    """
    today = date.today()
    total_months = 0

    for exp in experiences:
        if "인턴" in (exp.position or "") or "intern" in (exp.position or "").lower():
            continue
        try:
            start = date.fromisoformat(exp.start_date + "-01")
            end_str = exp.end_date if exp.end_date else today.strftime("%Y-%m")
            end = date.fromisoformat(end_str + "-01")
            total_months += (end.year - start.year) * 12 + (end.month - start.month) + 1
        except Exception:
            continue

    return round(total_months / 12, 1)


def structurize(text: str, source_format: str) -> ParsedResume:
    """텍스트를 LLM으로 구조화하여 ParsedResume 반환.

    GOOGLE_API_KEY 있으면 Gemini, 없으면 OPENAI_API_KEY로 자동 fallback.

    Args:
        text: 추출된 이력서 텍스트
        source_format: 원본 파일 형식 ("pdf", "docx", "md", "txt", "json")

    Raises:
        ResumeLLMError: API 키 없음 또는 LLM 호출 실패
    """
    try:
        result = generate_structured(text, schema=ParsedResume, system_prompt=_SYSTEM_PROMPT)
    except Exception as e:
        raise ResumeLLMError(stage="structurize", cause=e) from e

    result.source_format = source_format
    result.total_years_experience = _calc_experience_years(result.experiences)
    return result
