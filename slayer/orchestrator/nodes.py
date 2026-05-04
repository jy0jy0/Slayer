"""LangGraph node functions for the end-to-end pipeline.

Each node is a thin adapter that:
  1. Reads what it needs from the state
  2. Calls the existing agent / pipeline entry point
  3. Returns a partial-state dict that LangGraph merges back

No business logic lives here — the underlying agents and pipelines own
that. The orchestrator only wires their inputs and outputs together.

Errors inside a node are caught and recorded in `errors` rather than
raised, so a single failing step does not crash the whole pipeline.
Downstream nodes that depend on the missing output mark themselves as
skipped via `skipped_steps`.

LangGraph note: each node returns ONLY the keys it wants to update.
Fields not in the returned dict are preserved as-is. To append to
`errors` / `skipped_steps`, the node returns the full new list.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any, Awaitable, Callable, TypeVar

import httpx
import openai

from slayer.schemas import (
    CoverLetterInput,
    InterviewQuestionsInput,
    ResumeOptimizationInput,
)

from slayer.orchestrator.state import PipelineState

logger = logging.getLogger(__name__)


# Network-level errors that are worth one quick retry. Streaming SSE
# from OpenAI sometimes drops mid-message (RemoteProtocolError) on a
# wifi blip — observed on cover_letter_node 2026-05-04. Re-running the
# agent from scratch is idempotent, so a single retry is safe.
_TRANSIENT_NETWORK_ERRORS: tuple[type[BaseException], ...] = (
    httpx.RemoteProtocolError,
    httpx.ReadError,
    httpx.ConnectError,
    httpx.ConnectTimeout,
    openai.APIConnectionError,
    openai.APITimeoutError,
)

T = TypeVar("T")


async def _call_with_retry(
    fn: Callable[[], Awaitable[T]],
    *,
    step: str,
    max_attempts: int = 2,
    base_delay: float = 2.0,
) -> T:
    """Call an async LLM function once, retry once on transient network errors.

    Only retries network-layer errors. Domain errors (validation, parse
    failures, rate limit, auth) propagate immediately so they surface as
    real bugs.
    """
    last_exc: BaseException | None = None
    for attempt in range(1, max_attempts + 1):
        try:
            return await fn()
        except _TRANSIENT_NETWORK_ERRORS as exc:
            last_exc = exc
            if attempt == max_attempts:
                raise
            logger.warning(
                "%s attempt %d/%d hit transient network error (%s); retrying in %.1fs",
                step,
                attempt,
                max_attempts,
                type(exc).__name__,
                base_delay,
            )
            await asyncio.sleep(base_delay)
    # Unreachable — either returned or raised above.
    assert last_exc is not None
    raise last_exc


def _append_error(state: PipelineState, step: str, exc: Exception) -> list[str]:
    """Return the new `errors` list with this failure appended."""
    logger.exception("Step %s failed", step)
    errors = list(state.get("errors") or [])
    errors.append(f"{step}: {type(exc).__name__}: {exc}")
    return errors


def _append_skip(state: PipelineState, step: str, reason: str) -> list[str]:
    """Return the new `skipped_steps` list with this skip appended."""
    logger.warning("Step %s skipped: %s", step, reason)
    skipped = list(state.get("skipped_steps") or [])
    skipped.append(f"{step}: {reason}")
    return skipped


# ═══════════════════════════════════════════════════
# Stage nodes
# ═══════════════════════════════════════════════════


async def parse_jd_node(state: PipelineState) -> dict[str, Any]:
    """Scrape and parse the JD URL into a JDSchema."""
    from slayer.pipelines.jd_parser.scraper import scrape_jd_async

    url = state.get("jd_url")
    if not url:
        return {"jd": None, "skipped_steps": _append_skip(state, "parse_jd", "no jd_url provided")}

    try:
        jd = await scrape_jd_async(url)
        return {"jd": jd}
    except Exception as exc:
        return {"jd": None, "errors": _append_error(state, "parse_jd", exc)}


async def parse_resume_node(state: PipelineState) -> dict[str, Any]:
    """Parse the local resume file into a ParsedResume."""
    from slayer.pipelines.resume_parser import parse_resume

    path = state.get("resume_path")
    if not path:
        return {
            "resume": None,
            "skipped_steps": _append_skip(state, "parse_resume", "no resume_path provided"),
        }

    try:
        resume = parse_resume(path)
        return {"resume": resume}
    except Exception as exc:
        return {"resume": None, "errors": _append_error(state, "parse_resume", exc)}


async def company_research_node(state: PipelineState) -> dict[str, Any]:
    """Run the company research ReAct agent."""
    from slayer.agents.company_research.agent import run_company_research

    name = state.get("company_name")
    if not name:
        return {
            "company_research": None,
            "skipped_steps": _append_skip(state, "company_research", "no company_name provided"),
        }

    try:
        result = await _call_with_retry(
            lambda: run_company_research(name),
            step="company_research",
        )
        return {"company_research": result}
    except Exception as exc:
        return {
            "company_research": None,
            "errors": _append_error(state, "company_research", exc),
        }


async def match_node(state: PipelineState) -> dict[str, Any]:
    """Run the JD-resume matcher ReAct agent."""
    from slayer.pipelines.jd_resume_matcher.matcher import match_jd_resume

    jd = state.get("jd")
    resume = state.get("resume")
    if jd is None or resume is None:
        return {
            "match_result": None,
            "skipped_steps": _append_skip(state, "match", "missing jd or resume"),
        }

    try:
        result = await _call_with_retry(
            lambda: match_jd_resume(jd, resume),
            step="match",
        )
        return {"match_result": result}
    except Exception as exc:
        return {"match_result": None, "errors": _append_error(state, "match", exc)}


async def optimize_node(state: PipelineState) -> dict[str, Any]:
    """Run the resume optimizer ReAct agent.

    Skips when the current ATS score already meets target (saves cost).
    """
    from slayer.agents.resume_optimizer.agent import optimize_resume

    jd = state.get("jd")
    resume = state.get("resume")
    match_result = state.get("match_result")
    target = float(state.get("target_ats_score") or 80.0)

    if jd is None or resume is None or match_result is None:
        return {
            "optimization_result": None,
            "skipped_steps": _append_skip(state, "optimize", "missing jd/resume/match_result"),
        }

    if match_result.ats_score >= target:
        return {
            "optimization_result": None,
            "skipped_steps": _append_skip(
                state,
                "optimize",
                f"current score {match_result.ats_score:.1f} already meets target {target:.1f}",
            ),
        }

    try:
        opt_input = ResumeOptimizationInput(
            parsed_resume=resume,
            jd=jd,
            match_result=match_result,
            target_ats_score=target,
            max_iterations=int(state.get("max_optimization_iterations") or 3),
        )
        result = await _call_with_retry(
            lambda: optimize_resume(opt_input),
            step="optimize",
        )
        return {"optimization_result": result}
    except Exception as exc:
        return {
            "optimization_result": None,
            "errors": _append_error(state, "optimize", exc),
        }


async def cover_letter_node(state: PipelineState) -> dict[str, Any]:
    """Run the cover letter ReAct agent."""
    from slayer.agents.cover_letter.agent import generate_cover_letter

    jd = state.get("jd")
    resume = state.get("resume")
    research = state.get("company_research")
    match_result = state.get("match_result")

    if any(x is None for x in (jd, resume, research, match_result)):
        return {
            "cover_letter": None,
            "skipped_steps": _append_skip(
                state,
                "cover_letter",
                "missing jd/resume/company_research/match_result",
            ),
        }

    try:
        cl_input = CoverLetterInput(
            parsed_resume=resume,
            jd=jd,
            company_research=research,
            match_result=match_result,
        )
        result = await _call_with_retry(
            lambda: generate_cover_letter(cl_input),
            step="cover_letter",
        )
        return {"cover_letter": result}
    except Exception as exc:
        return {"cover_letter": None, "errors": _append_error(state, "cover_letter", exc)}


async def interview_questions_node(state: PipelineState) -> dict[str, Any]:
    """Generate interview questions (sync pipeline wrapped in async)."""
    import asyncio

    from slayer.pipelines.interview_questions.generator import (
        generate_interview_questions,
    )

    jd = state.get("jd")
    resume = state.get("resume")
    if jd is None or resume is None:
        return {
            "interview_questions": None,
            "skipped_steps": _append_skip(state, "interview_questions", "missing jd or resume"),
        }

    iq_input = InterviewQuestionsInput(
        jd=jd,
        resume=resume,
        company_research=state.get("company_research"),
        match_result=state.get("match_result"),
    )

    try:
        # generate_interview_questions is sync — run it in a thread to
        # avoid blocking the orchestrator's event loop.
        result = await _call_with_retry(
            lambda: asyncio.to_thread(generate_interview_questions, iq_input),
            step="interview_questions",
        )
        return {"interview_questions": result}
    except Exception as exc:
        return {
            "interview_questions": None,
            "errors": _append_error(state, "interview_questions", exc),
        }
