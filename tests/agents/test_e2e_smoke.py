"""End-to-end smoke tests for the agent pipeline.

These tests verify that all agents can be built and their inputs/outputs
are schema-compatible, without actually invoking the LLM. They catch
integration issues (broken imports, schema mismatches, builder wiring)
that unit tests miss.

Set SLAYER_SKIP_E2E=1 to skip these tests (e.g. in fast CI loops).
"""

from __future__ import annotations

import os

import pytest

from slayer.agents.company_research.agent import build_company_research_agent
from slayer.agents.cover_letter.agent import build_cover_letter_agent
from slayer.agents.resume_optimizer.agent import build_resume_optimizer_agent
from slayer.pipelines.jd_resume_matcher.matcher import (
    build_matcher_agent,
    create_mock_match_result,
)
from slayer.schemas import (
    CompanyResearchOutput,
    CoverLetterInput,
    CoverLetterOutput,
    MatchResult,
    ResumeOptimizationInput,
    ResumeOptimizationOutput,
    parsed_resume_to_blocks,
)
from slayer.ui.events import EventType

SKIP_E2E = os.environ.get("SLAYER_SKIP_E2E") == "1"
pytestmark = pytest.mark.skipif(SKIP_E2E, reason="E2E smoke disabled by env var")


class TestAllAgentsBuild:
    """All four ReAct agents must be buildable from the same process."""

    def test_all_builders_return_compiled_graph(self):
        builders = [
            ("company_research", build_company_research_agent),
            ("resume_optimizer", build_resume_optimizer_agent),
            ("cover_letter", build_cover_letter_agent),
            ("matcher", build_matcher_agent),
        ]
        for name, builder in builders:
            agent = builder()
            # All 4 ReAct agents must remain CompiledStateGraph so existing
            # isinstance/type-name checks in unit tests keep working.
            assert type(agent).__name__ == "CompiledStateGraph", (
                f"{name}: expected CompiledStateGraph, got {type(agent).__name__}"
            )
            # Agents must expose astream_events and ainvoke for runtime use.
            assert hasattr(agent, "astream_events"), f"{name} missing astream_events"
            assert hasattr(agent, "ainvoke"), f"{name} missing ainvoke"


class TestSchemaPipelineChain:
    """Schemas must chain together across the full pipeline without mutation."""

    def test_match_result_feeds_into_optimization_input(
        self, sample_jd, sample_resume, sample_match_result
    ):
        """Matcher output must be a valid ResumeOptimizationInput field."""
        opt_input = ResumeOptimizationInput(
            parsed_resume=sample_resume,
            jd=sample_jd,
            match_result=sample_match_result,
            target_ats_score=80.0,
            max_iterations=3,
        )
        assert opt_input.match_result.ats_score == sample_match_result.ats_score
        assert opt_input.target_ats_score == 80.0

    def test_optimization_output_blocks_convert_back(self, sample_resume):
        """parsed_resume_to_blocks → ResumeOptimizationOutput round-trips."""
        blocks = parsed_resume_to_blocks(sample_resume)
        assert len(blocks) > 0
        out = ResumeOptimizationOutput(
            optimized_blocks=blocks,
            final_ats_score=85.0,
            score_improvement=20.0,
            iterations_used=2,
            optimization_summary="test",
        )
        # Output must preserve the block count and scores.
        assert len(out.optimized_blocks) == len(blocks)
        assert out.final_ats_score == 85.0

    def test_cover_letter_input_accepts_all_upstream_outputs(
        self, sample_jd, sample_resume, sample_company_research, sample_match_result
    ):
        """Cover letter input must accept outputs from research + match."""
        cl_input = CoverLetterInput(
            parsed_resume=sample_resume,
            jd=sample_jd,
            company_research=sample_company_research,
            match_result=sample_match_result,
        )
        assert cl_input.company_research.company_name == "카카오"
        assert cl_input.match_result.ats_score == sample_match_result.ats_score


class TestMockMatchResult:
    """The mock matcher result stays compatible with the real MatchResult schema."""

    def test_mock_match_result_is_valid_schema(self):
        result = create_mock_match_result()
        assert isinstance(result, MatchResult)
        assert 0 <= result.ats_score <= 100
        # score_breakdown should sum approximately to ats_score.
        total = sum(result.score_breakdown.values())
        assert abs(total - result.ats_score) < 1e-6


class TestEventTypeIntegration:
    """EventType enum is backward-compatible with legacy string comparisons."""

    def test_enum_equals_legacy_string(self):
        assert EventType.THINKING == "thinking"
        assert EventType.TOOL_CALL == "tool_call"
        assert EventType.TOOL_RESULT == "tool_result"
        assert EventType.DONE == "done"

    def test_enum_works_as_dict_key(self):
        d = {
            EventType.THINKING: 1,
            EventType.TOOL_CALL: 2,
        }
        assert d.get("thinking") == 1
        assert d.get("tool_call") == 2
