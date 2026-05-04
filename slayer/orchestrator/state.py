"""Orchestrator pipeline state.

Single source of truth for the data that flows through the LangGraph
end-to-end pipeline. Each node reads what it needs and writes its own
output back to this state. Optional fields stay None until the node
that produces them runs.
"""

from __future__ import annotations

from typing import Optional, TypedDict

from slayer.schemas import (
    CompanyResearchOutput,
    CoverLetterOutput,
    InterviewQuestionsOutput,
    JDSchema,
    MatchResult,
    ParsedResume,
    ResumeOptimizationOutput,
)


class PipelineState(TypedDict, total=False):
    """End-to-end pipeline state.

    `total=False` so nodes can populate fields incrementally. The graph
    starts with only the input fields populated.
    """

    # ── Inputs ──────────────────────────────────────
    company_name: str
    jd_url: str
    resume_path: str
    target_ats_score: float
    max_optimization_iterations: int

    # ── Stage outputs ───────────────────────────────
    jd: Optional[JDSchema]
    resume: Optional[ParsedResume]
    company_research: Optional[CompanyResearchOutput]
    match_result: Optional[MatchResult]
    optimization_result: Optional[ResumeOptimizationOutput]
    cover_letter: Optional[CoverLetterOutput]
    interview_questions: Optional[InterviewQuestionsOutput]

    # ── Meta ────────────────────────────────────────
    errors: list[str]
    skipped_steps: list[str]


def build_initial_state(
    company_name: str,
    jd_url: str,
    resume_path: str,
    target_ats_score: float = 80.0,
    max_optimization_iterations: int = 3,
) -> PipelineState:
    """Construct the initial state from user inputs."""
    return PipelineState(
        company_name=company_name,
        jd_url=jd_url,
        resume_path=resume_path,
        target_ats_score=target_ats_score,
        max_optimization_iterations=max_optimization_iterations,
        jd=None,
        resume=None,
        company_research=None,
        match_result=None,
        optimization_result=None,
        cover_letter=None,
        interview_questions=None,
        errors=[],
        skipped_steps=[],
    )
