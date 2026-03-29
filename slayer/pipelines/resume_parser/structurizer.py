"""추출된 텍스트 → Gemini structured output → ParsedResume.

google-genai SDK의 response_schema를 활용하여
JSON 파싱 오류 없이 ParsedResume을 생성합니다.
"""

from __future__ import annotations

from datetime import date

from google import genai
from google.genai.types import GenerateContentConfig

from slayer.config import GOOGLE_API_KEY
from slayer.pipelines.resume_parser.file_detector import ResumeLLMError
from slayer.schemas import ExperienceItem, ParsedResume

_MODEL = "gemini-2.5-flash"

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
    """텍스트를 Gemini로 구조화하여 ParsedResume 반환.

    Args:
        text: 추출된 이력서 텍스트
        source_format: 원본 파일 형식 ("pdf", "docx", "md", "txt")

    Raises:
        ResumeLLMError: Gemini API 호출 또는 응답 파싱 실패
    """
    client = genai.Client(api_key=GOOGLE_API_KEY)

    try:
        response = client.models.generate_content(
            model=_MODEL,
            contents=text,
            config=GenerateContentConfig(
                system_instruction=_SYSTEM_PROMPT,
                response_mime_type="application/json",
                response_schema=ParsedResume,
                temperature=0.0,
            ),
        )
    except Exception as e:
        raise ResumeLLMError(stage="structurize", cause=e) from e

    try:
        result = ParsedResume.model_validate_json(response.text)
    except Exception as e:
        raise ResumeLLMError(stage="structurize", cause=e) from e

    result.source_format = source_format
    result.total_years_experience = _calc_experience_years(result.experiences)
    return result
