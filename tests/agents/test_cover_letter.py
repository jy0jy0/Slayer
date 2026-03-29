"""Cover Letter ReAct Agent tests."""

from slayer.agents.cover_letter.agent import build_cover_letter_agent
from slayer.schemas import CoverLetterOutput, JDSchema, JDRequirements


def test_react_agent_builds():
    agent = build_cover_letter_agent()
    assert agent is not None
    assert type(agent).__name__ == "CompiledStateGraph"


def test_cover_letter_output_schema():
    output = CoverLetterOutput(
        cover_letter="Hello.", key_points=["diligent"],
        jd_keyword_coverage=0.5, word_count=6,
    )
    assert output.cover_letter == "Hello."
    assert output.jd_keyword_coverage == 0.5
