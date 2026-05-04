"""Regression tests for interview_questions/generator.py JSON parsing.

Issue observed 2026-05-04 in the wanted-URL demo run: Gemini sometimes
emits long Korean answers with raw control characters (unescaped \n
inside string literals). The fix is `json.loads(..., strict=False)`
plus stripping ```json``` fences via parse_agent_json.
"""

from __future__ import annotations

from unittest.mock import patch

import pytest

from slayer.pipelines.interview_questions.generator import (
    generate_interview_questions,
)
from slayer.schemas import (
    InterviewCategory,
    InterviewQuestionsInput,
    JDOverview,
    JDRequirements,
    JDSchema,
    ParsedResume,
    PersonalInfo,
)


# ── Minimal fixtures ─────────────────────────────────────


@pytest.fixture
def minimal_input() -> InterviewQuestionsInput:
    jd = JDSchema(
        company="카카오",
        title="백엔드",
        position="서버",
        overview=JDOverview(employment_type="정규직"),
        responsibilities=["API 개발"],
        requirements=JDRequirements(required=["Python"], preferred=[]),
        skills=["python"],
        process=[],
        platform="wanted",
    )
    resume = ParsedResume(
        personal_info=PersonalInfo(name="테스트"),
        skills=["python"],
        total_years_experience=2.0,
    )
    return InterviewQuestionsInput(
        jd=jd,
        resume=resume,
        # Restrict to 1 category × 1 question to keep stub responses short.
        categories=[InterviewCategory.TECHNICAL],
        questions_per_category=1,
    )


# ── A fake provider whose response we control ────────────


class _StubProvider:
    def __init__(self, response: str) -> None:
        self._response = response

    def generate_json(self, prompt: str) -> str:
        return self._response


# ── Tests ────────────────────────────────────────────────


def test_parses_clean_json(minimal_input):
    """Plain JSON with no fences and no control chars works as before."""
    response = """{
        "questions": [
            {
                "category": "기술",
                "question": "FastAPI 의존성 주입을 설명해주세요.",
                "intent": "기본기 확인",
                "tip": "Depends 예시 1개 준비",
                "source": "resume_skill: python"
            }
        ],
        "sample_answers": [],
        "weak_areas": []
    }"""
    out = generate_interview_questions(minimal_input, provider=_StubProvider(response))
    assert len(out.questions) == 1
    assert out.questions[0].category == InterviewCategory.TECHNICAL


def test_parses_response_wrapped_in_json_fence(minimal_input):
    """Gemini sometimes wraps JSON in ```json``` fences — we strip them."""
    response = """```json
{
    "questions": [
        {
            "category": "기술",
            "question": "테스트 질문입니다.",
            "intent": "intent",
            "tip": "tip",
            "source": "src"
        }
    ],
    "sample_answers": [],
    "weak_areas": []
}
```"""
    out = generate_interview_questions(minimal_input, provider=_StubProvider(response))
    assert len(out.questions) == 1


def test_parses_response_with_unescaped_control_chars(minimal_input):
    """Gemini occasionally emits raw \\n inside string literals.

    Standard json.loads rejects these (`Invalid control character`).
    `strict=False` accepts them — this is the regression case from the
    2026-05-04 wanted run.
    """
    # Note: the literal newline INSIDE a JSON string value is the bug
    # we're protecting against. Without strict=False, json.loads raises
    # "Invalid control character at: line N column M".
    response = (
        '{"questions": [{"category": "기술", "question": "한 줄\n두 줄", '
        '"intent": "intent", "tip": "tip", "source": "src"}], '
        '"sample_answers": [], "weak_areas": []}'
    )
    out = generate_interview_questions(minimal_input, provider=_StubProvider(response))
    assert len(out.questions) == 1
    assert "두 줄" in out.questions[0].question


def test_logs_first_chars_on_malformed_json(minimal_input, caplog):
    """Malformed-but-recognizable JSON should log a truncated preview before raising."""
    import logging

    # Looks like JSON (passes parse_agent_json's `{...}` heuristic) but is
    # not actually valid — this is the path that hits json.loads and the
    # "first 800 chars" log message.
    bad_response = '{"questions": [{"category": "기술", "question": "broken'
    with caplog.at_level(logging.ERROR):
        with pytest.raises(Exception):
            generate_interview_questions(
                minimal_input, provider=_StubProvider(bad_response)
            )
    # Earlier code logged the entire raw response; the fix truncates to 800 chars.
    assert any("first 800 chars" in r.message for r in caplog.records)
