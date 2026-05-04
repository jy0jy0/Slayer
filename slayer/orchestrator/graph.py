"""End-to-end pipeline LangGraph builder.

Wires the seven stage nodes into a single executable graph:

  parse_jd ─┐
            ├─► match ─► company_research ─► optimize? ─► cover_letter ─► interview_questions ─► END
  parse_resume ─┘

`parse_jd` and `parse_resume` run in parallel (both have START as their
only predecessor and feed independent state fields). All later steps
are sequential because each one consumes the previous outputs.

LangSmith tracing is automatic: when the LANGCHAIN_TRACING_V2 / API_KEY
environment variables are set, every node invocation is traced. When
they are not set, the graph runs identically without tracing.
"""

from __future__ import annotations

import logging
from typing import Any

from langgraph.graph import END, START, StateGraph

from slayer.orchestrator.nodes import (
    company_research_node,
    cover_letter_node,
    interview_questions_node,
    match_node,
    optimize_node,
    parse_jd_node,
    parse_resume_node,
)
from slayer.orchestrator.state import PipelineState, build_initial_state

logger = logging.getLogger(__name__)

# Cap on graph traversal length — protects against infinite loops if
# someone later adds a cycle. Pipeline today is acyclic so 25 is plenty.
RUNTIME_CONFIG = {"recursion_limit": 25}


def build_pipeline_graph():
    """Build and compile the end-to-end orchestrator graph."""
    graph = StateGraph(PipelineState)

    graph.add_node("parse_jd", parse_jd_node)
    graph.add_node("parse_resume", parse_resume_node)
    graph.add_node("match", match_node)
    graph.add_node("company_research", company_research_node)
    graph.add_node("optimize", optimize_node)
    graph.add_node("cover_letter", cover_letter_node)
    graph.add_node("interview_questions", interview_questions_node)

    # Parallel start: both parsers fan out from START.
    graph.add_edge(START, "parse_jd")
    graph.add_edge(START, "parse_resume")

    # Match needs both parsers — LangGraph waits until both feed into it.
    graph.add_edge("parse_jd", "match")
    graph.add_edge("parse_resume", "match")

    # Sequential tail.
    graph.add_edge("match", "company_research")
    graph.add_edge("company_research", "optimize")
    graph.add_edge("optimize", "cover_letter")
    graph.add_edge("cover_letter", "interview_questions")
    graph.add_edge("interview_questions", END)

    return graph.compile()


async def run_pipeline(
    company_name: str,
    jd_url: str,
    resume_path: str,
    target_ats_score: float = 80.0,
    max_optimization_iterations: int = 3,
) -> PipelineState:
    """Run the full pipeline and return the final state.

    Convenience wrapper for callers that don't want to assemble the
    graph themselves. The returned state contains every stage output
    plus `errors` / `skipped_steps` for inspection.
    """
    graph = build_pipeline_graph()
    initial = build_initial_state(
        company_name=company_name,
        jd_url=jd_url,
        resume_path=resume_path,
        target_ats_score=target_ats_score,
        max_optimization_iterations=max_optimization_iterations,
    )

    result: dict[str, Any] = await graph.ainvoke(initial, config=RUNTIME_CONFIG)
    return result  # type: ignore[return-value]
