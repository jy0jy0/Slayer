"""Unit tests for the orchestrator graph.

These tests patch every stage entry point so the graph runs without
hitting LLMs, web scrapers, or the file system. The goal is to verify
the wiring (state propagation, error capture, skip behavior) — not the
underlying agents, which have their own tests.
"""

from __future__ import annotations

import asyncio
from unittest.mock import patch

import pytest

from slayer.orchestrator import build_pipeline_graph, run_pipeline
from slayer.orchestrator.state import build_initial_state
from slayer.schemas import (
    BasicInfo,
    BlockChange,
    CompanyResearchOutput,
    CoverLetterOutput,
    InterviewCategory,
    InterviewQuestion,
    InterviewQuestionsOutput,
    JDOverview,
    JDRequirements,
    JDSchema,
    MatchResult,
    ParsedResume,
    PersonalInfo,
    ResumeOptimizationOutput,
    SampleAnswer,
)


# ═══════════════════════════════════════════════════
# Fixtures — minimal valid stage outputs
# ═══════════════════════════════════════════════════


@pytest.fixture
def fake_jd() -> JDSchema:
    return JDSchema(
        company="카카오",
        title="백엔드",
        position="서버",
        overview=JDOverview(employment_type="정규직"),
        responsibilities=["API 개발"],
        requirements=JDRequirements(required=["Python"], preferred=["AWS"]),
        skills=["python"],
        process=["서류"],
        platform="wanted",
    )


@pytest.fixture
def fake_resume() -> ParsedResume:
    return ParsedResume(
        personal_info=PersonalInfo(name="테스트"),
        skills=["python"],
        total_years_experience=2.0,
    )


@pytest.fixture
def fake_match() -> MatchResult:
    return MatchResult(
        ats_score=72.0,
        score_breakdown={
            "ats_simulation": 20.0,
            "keywords": 18.0,
            "experience": 16.0,
            "industry_specific": 10.0,
            "content": 5.0,
            "format": 2.0,
            "errors": 1.0,
        },
        matched_keywords=["python"],
        missing_keywords=["aws"],
        strengths=["python"],
        weaknesses=["aws"],
        gap_summary="ok",
    )


@pytest.fixture
def fake_high_match() -> MatchResult:
    """Match result that already meets the default 80 target."""
    return MatchResult(
        ats_score=92.0,
        score_breakdown={
            "ats_simulation": 28.0,
            "keywords": 24.0,
            "experience": 19.0,
            "industry_specific": 14.0,
            "content": 4.0,
            "format": 2.0,
            "errors": 1.0,
        },
        matched_keywords=["python", "aws"],
        missing_keywords=[],
        strengths=["all"],
        weaknesses=[],
        gap_summary="strong",
    )


@pytest.fixture
def fake_research() -> CompanyResearchOutput:
    return CompanyResearchOutput(
        company_name="카카오",
        basic_info=BasicInfo(industry="IT"),
        summary="플랫폼 기업",
        data_sources=["mock"],
        researched_at="2026-04-01T00:00:00",
    )


@pytest.fixture
def fake_optimization() -> ResumeOptimizationOutput:
    return ResumeOptimizationOutput(
        optimized_blocks=[],
        final_ats_score=85.0,
        score_improvement=13.0,
        changes=[],
        iterations_used=2,
        optimization_summary="optimized",
    )


@pytest.fixture
def fake_cover_letter() -> CoverLetterOutput:
    return CoverLetterOutput(
        cover_letter="안녕하세요...",
        key_points=["a", "b", "c"],
        jd_keyword_coverage=0.6,
        word_count=900,
    )


@pytest.fixture
def fake_interview_questions() -> InterviewQuestionsOutput:
    return InterviewQuestionsOutput(
        questions=[
            InterviewQuestion(
                category=InterviewCategory.TECHNICAL,
                question="FastAPI 의 의존성 주입을 설명해주세요.",
                intent="기본기 확인",
                tip="구체 예시 1개 준비",
                source="resume_skill: fastapi",
            ),
        ],
        sample_answers=[
            SampleAnswer(
                question="FastAPI 의 의존성 주입을 설명해주세요.",
                answer="Depends() 를 사용하여...",
            ),
        ],
        weak_areas=[],
        excluded_categories=[],
    )


# ═══════════════════════════════════════════════════
# Graph structure
# ═══════════════════════════════════════════════════


class TestGraphStructure:
    def test_compiles_to_state_graph(self):
        graph = build_pipeline_graph()
        # Public LangGraph type contract preserved (existing repo tests
        # rely on this name-based check pattern).
        assert type(graph).__name__ == "CompiledStateGraph"

    def test_all_nodes_registered(self):
        graph = build_pipeline_graph()
        expected = {
            "parse_jd",
            "parse_resume",
            "match",
            "company_research",
            "optimize",
            "cover_letter",
            "interview_questions",
        }
        # __start__ / __end__ may also appear; subset check is enough.
        assert expected.issubset(set(graph.nodes.keys()))


# ═══════════════════════════════════════════════════
# End-to-end happy path (everything mocked)
# ═══════════════════════════════════════════════════


class TestHappyPath:
    def test_full_pipeline_populates_every_stage(
        self,
        fake_jd,
        fake_resume,
        fake_match,
        fake_research,
        fake_optimization,
        fake_cover_letter,
        fake_interview_questions,
    ):
        async def _scrape(*_args, **_kw):
            return fake_jd

        async def _research(*_args, **_kw):
            return fake_research

        async def _match(*_args, **_kw):
            return fake_match

        async def _optimize(*_args, **_kw):
            return fake_optimization

        async def _cover(*_args, **_kw):
            return fake_cover_letter

        with patch(
            "slayer.orchestrator.nodes.scrape_jd_async",
            new=_scrape,
            create=True,
        ), patch(
            "slayer.pipelines.jd_parser.scraper.scrape_jd_async",
            new=_scrape,
        ), patch(
            "slayer.pipelines.resume_parser.parse_resume",
            return_value=fake_resume,
        ), patch(
            "slayer.agents.company_research.agent.run_company_research",
            new=_research,
        ), patch(
            "slayer.pipelines.jd_resume_matcher.matcher.match_jd_resume",
            new=_match,
        ), patch(
            "slayer.agents.resume_optimizer.agent.optimize_resume",
            new=_optimize,
        ), patch(
            "slayer.agents.cover_letter.agent.generate_cover_letter",
            new=_cover,
        ), patch(
            "slayer.pipelines.interview_questions.generator.generate_interview_questions",
            return_value=fake_interview_questions,
        ):
            final = asyncio.run(
                run_pipeline(
                    company_name="카카오",
                    jd_url="https://example.com/jd/1",
                    resume_path="/tmp/fake.pdf",
                    target_ats_score=80.0,
                )
            )

        assert final["jd"] is not None
        assert final["resume"] is not None
        assert final["match_result"].ats_score == 72.0
        assert final["company_research"].company_name == "카카오"
        assert final["optimization_result"].final_ats_score == 85.0
        assert final["cover_letter"].word_count == 900
        assert final["interview_questions"] is not None
        assert final["errors"] == []


# ═══════════════════════════════════════════════════
# Skip behavior — already meets target ATS score
# ═══════════════════════════════════════════════════


class TestSkipOptimization:
    def test_optimize_skipped_when_score_meets_target(
        self,
        fake_jd,
        fake_resume,
        fake_high_match,
        fake_research,
        fake_cover_letter,
        fake_interview_questions,
    ):
        async def _scrape(*_args, **_kw):
            return fake_jd

        async def _research(*_args, **_kw):
            return fake_research

        async def _match(*_args, **_kw):
            return fake_high_match

        async def _cover(*_args, **_kw):
            return fake_cover_letter

        with patch(
            "slayer.pipelines.jd_parser.scraper.scrape_jd_async",
            new=_scrape,
        ), patch(
            "slayer.pipelines.resume_parser.parse_resume",
            return_value=fake_resume,
        ), patch(
            "slayer.agents.company_research.agent.run_company_research",
            new=_research,
        ), patch(
            "slayer.pipelines.jd_resume_matcher.matcher.match_jd_resume",
            new=_match,
        ), patch(
            "slayer.agents.cover_letter.agent.generate_cover_letter",
            new=_cover,
        ), patch(
            "slayer.pipelines.interview_questions.generator.generate_interview_questions",
            return_value=fake_interview_questions,
        ):
            final = asyncio.run(
                run_pipeline(
                    company_name="카카오",
                    jd_url="https://example.com/jd/2",
                    resume_path="/tmp/fake.pdf",
                    target_ats_score=80.0,
                )
            )

        # Optimization was skipped because the match already meets target.
        assert final["optimization_result"] is None
        assert any("optimize" in s for s in final["skipped_steps"])
        # Downstream stages still ran.
        assert final["cover_letter"] is not None
        assert final["interview_questions"] is not None


# ═══════════════════════════════════════════════════
# Error containment — one failing stage doesn't crash the graph
# ═══════════════════════════════════════════════════


class TestErrorContainment:
    def test_jd_parse_failure_skips_dependents_but_records_error(
        self,
        fake_resume,
    ):
        async def _failing_scrape(*_args, **_kw):
            raise RuntimeError("crawl4ai exploded")

        with patch(
            "slayer.pipelines.jd_parser.scraper.scrape_jd_async",
            new=_failing_scrape,
        ), patch(
            "slayer.pipelines.resume_parser.parse_resume",
            return_value=fake_resume,
        ):
            final = asyncio.run(
                run_pipeline(
                    company_name="카카오",
                    jd_url="https://example.com/broken",
                    resume_path="/tmp/fake.pdf",
                )
            )

        assert final["jd"] is None
        # Resume parsing still succeeded thanks to parallel fan-out.
        assert final["resume"] is not None
        # The error is captured in state, not raised.
        assert any("parse_jd" in e for e in final["errors"])
        # Match needs both jd and resume — must be skipped.
        assert final["match_result"] is None
        assert any("match" in s for s in final["skipped_steps"])


# ═══════════════════════════════════════════════════
# Transient network error retry (issue #3 from 2026-05-04 demo run)
# ═══════════════════════════════════════════════════


class TestTransientRetry:
    """Transient httpx errors mid-stream must be retried once before giving up."""

    def test_match_retries_on_remote_protocol_error(
        self,
        fake_jd,
        fake_resume,
        fake_match,
    ):
        """First call raises httpx.RemoteProtocolError, second succeeds."""
        import httpx

        async def _scrape(*_a, **_kw):
            return fake_jd

        call_count = {"n": 0}

        async def _flaky_match(*_a, **_kw):
            call_count["n"] += 1
            if call_count["n"] == 1:
                raise httpx.RemoteProtocolError("peer closed mid-stream")
            return fake_match

        with patch(
            "slayer.pipelines.jd_parser.scraper.scrape_jd_async", new=_scrape,
        ), patch(
            "slayer.pipelines.resume_parser.parse_resume", return_value=fake_resume,
        ), patch(
            "slayer.pipelines.jd_resume_matcher.matcher.match_jd_resume",
            new=_flaky_match,
        ), patch(
            "slayer.orchestrator.nodes.asyncio.sleep", new=_noop_sleep,
        ), patch(
            "slayer.agents.company_research.agent.run_company_research",
            new=_async_value(None),
        ), patch(
            "slayer.agents.resume_optimizer.agent.optimize_resume",
            new=_async_value(None),
        ), patch(
            "slayer.agents.cover_letter.agent.generate_cover_letter",
            new=_async_value(None),
        ), patch(
            "slayer.pipelines.interview_questions.generator.generate_interview_questions",
            return_value=None,
        ):
            final = asyncio.run(
                run_pipeline(
                    company_name="카카오",
                    jd_url="https://example.com/jd/3",
                    resume_path="/tmp/fake.pdf",
                )
            )

        # Match was called twice: once that failed, once that succeeded.
        assert call_count["n"] == 2
        assert final["match_result"] is not None
        # No error should be recorded for match — it succeeded after retry.
        assert not any("match:" in e for e in final["errors"])

    def test_match_gives_up_after_two_attempts(
        self,
        fake_jd,
        fake_resume,
    ):
        """Two consecutive transient errors → propagate as recorded error."""
        import httpx

        async def _scrape(*_a, **_kw):
            return fake_jd

        call_count = {"n": 0}

        async def _always_flaky(*_a, **_kw):
            call_count["n"] += 1
            raise httpx.RemoteProtocolError("peer closed mid-stream")

        with patch(
            "slayer.pipelines.jd_parser.scraper.scrape_jd_async", new=_scrape,
        ), patch(
            "slayer.pipelines.resume_parser.parse_resume", return_value=fake_resume,
        ), patch(
            "slayer.pipelines.jd_resume_matcher.matcher.match_jd_resume",
            new=_always_flaky,
        ), patch(
            "slayer.orchestrator.nodes.asyncio.sleep", new=_noop_sleep,
        ), patch(
            # Stub downstream nodes so they short-circuit without LLM calls.
            # match_result is None will already make most of them skip, but
            # company_research uses company_name (not match_result), so it
            # would otherwise hit the real OpenAI agent.
            "slayer.agents.company_research.agent.run_company_research",
            new=_async_value(None),
        ), patch(
            "slayer.agents.cover_letter.agent.generate_cover_letter",
            new=_async_value(None),
        ), patch(
            "slayer.pipelines.interview_questions.generator.generate_interview_questions",
            return_value=None,
        ):
            final = asyncio.run(
                run_pipeline(
                    company_name="카카오",
                    jd_url="https://example.com/jd/4",
                    resume_path="/tmp/fake.pdf",
                )
            )

        # Default is 2 attempts (1 initial + 1 retry).
        assert call_count["n"] == 2
        assert final["match_result"] is None
        assert any("RemoteProtocolError" in e for e in final["errors"])


# Helpers used by the retry tests above.
async def _noop_sleep(*_a, **_kw):
    """Replacement for asyncio.sleep that returns immediately."""
    return None


def _async_value(v):
    """Wrap a value as a callable that returns it via an awaitable."""
    async def _f(*_a, **_kw):
        return v
    return _f
