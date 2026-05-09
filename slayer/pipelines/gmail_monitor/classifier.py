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
You are an expert recruitment process assistant.

STEP 1 — GATE CHECK (most important):
First, decide if this email is part of a formal company hiring/recruitment process.
It MUST be one of:
  - A result notification for a job application stage (pass/fail/reject)
  - An invitation to a job interview (1st, 2nd, final, etc.)
  - A formal job offer letter

It is NOT recruitment if it is any of:
  - Marketing emails, newsletters, promotions
  - Study programs, hackathons, events, workshops
  - Welcome emails for non-job services (cloud credits, platforms, tools)
  - GitHub notifications, community invitations
  - Any email where you did NOT apply for a job position

If it fails the gate check → set company="NOT_RECRUITMENT", status_type=REJECT,
raw_summary="채용 프로세스 이메일이 아님" and stop.

STEP 2 — EXTRACT (only if passed gate):
1. company: The company name you applied to for a job.
2. status_type: PASS / FAIL / INTERVIEW / REJECT
   - PASS: Passed a specific hiring stage
   - FAIL: Failed a specific stage
   - INTERVIEW: Invited to an interview with scheduled time
   - REJECT: Rejected without a specific stage
3. stage_name: e.g. "서류전형", "코딩테스트", "1차면접"
4. next_step: Next steps mentioned in the email.
5. interview_details: Only for INTERVIEW status.
   - datetime_str: ISO8601 (e.g. "2026-04-15T14:00:00+09:00")
   - location, format ("online"/"offline"), platform, duration_minutes
6. raw_summary: One-sentence Korean summary.

Constraints:
- Respond ONLY with the JSON structure.
- Use null for missing optional fields.
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
