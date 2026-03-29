"""LLM 기반 이메일 분류 (합격/불합격/면접 안내).

Gmail의 제목과 내용을 분석하여 채용 상태 변화를 구조화합니다.
"""

from __future__ import annotations

from google import genai
from google.genai.types import GenerateContentConfig

from slayer.config import GOOGLE_API_KEY
from slayer.schemas import GmailParseResult

_MODEL = "gemini-2.5-flash"

_SYSTEM_PROMPT = """\
You are an expert recruitment process assistant. Analyze the email subject and body provided below to extract recruitment status changes.

Rules:
1. company: Extract the company name (e.g., "Samsung Electronics", "Toss").
2. status_type: Categorize into PASS, FAIL, INTERVIEW, or REJECT.
   - PASS: Success in a specific stage (e.g., "Passed document screening").
   - FAIL: Failed in a specific stage or the final process.
   - INTERVIEW: Scheduled for an interview (1st, 2nd, etc.).
   - REJECT: Immediate rejection without a specific stage mentioned.
3. stage_name: Extract the recruitment stage (e.g., "Document Screening", "Coding Test", "1st Interview").
4. next_step: Briefly summarize the next steps mentioned.
5. interview_details: If it's an INTERVIEW status, extract the following:
   - datetime_str: ISO8601 format (e.g., "2026-03-30T14:00:00+09:00").
   - location: Address or online link.
   - format: "online" or "offline".
   - platform: "Zoom", "Google Meet", etc.
   - duration_minutes: Expected duration in minutes.
6. raw_summary: Provide a concise one-sentence summary of the email content in Korean.

Constraints:
- Respond ONLY with the requested JSON structure.
- If information is missing, use null for optional fields.
- Use the provided context to calculate dates if relative terms like "next Monday" are used.
"""


class GmailParseError(Exception):
    """Gmail 파싱 중 발생하는 예외."""

    def __init__(self, stage: str, cause: Exception):
        self.stage = stage
        self.cause = cause
        super().__init__(f"Gmail parsing failed at {stage}: {cause}")


def classify_email(subject: str, body: str, context_date: str = None) -> GmailParseResult:
    """이메일 내용을 분석하여 GmailParseResult 반환.

    Args:
        subject: 이메일 제목
        body: 이메일 본문
        context_date: 상대 날짜 계산을 위한 기준일 (ISO8601)

    Raises:
        GmailParseError: Gemini API 호출 또는 응답 파싱 실패
    """
    client = genai.Client(api_key=GOOGLE_API_KEY)

    prompt = f"Subject: {subject}\n\nBody: {body}"
    if context_date:
        prompt = f"Context Date: {context_date}\n\n{prompt}"

    try:
        response = client.models.generate_content(
            model=_MODEL,
            contents=prompt,
            config=GenerateContentConfig(
                system_instruction=_SYSTEM_PROMPT,
                response_mime_type="application/json",
                response_schema=GmailParseResult,
                temperature=0.0,
            ),
        )
    except Exception as e:
        raise GmailParseError(stage="llm_generation", cause=e) from e

    try:
        result = GmailParseResult.model_validate_json(response.text)
    except Exception as e:
        # LLM이 잘못된 JSON을 반환하거나 스키마에 맞지 않을 때
        raise GmailParseError(stage="schema_validation", cause=e) from e

    return result
