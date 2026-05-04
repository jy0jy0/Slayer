"""End-to-end pipeline orchestrator built on LangGraph.

Wires the existing stage agents/pipelines (JD parser, resume parser,
matcher, company research, resume optimizer, cover letter, interview
questions) into a single graph that can be invoked once.

Public entry points:
    from slayer.orchestrator import build_pipeline_graph, run_pipeline
"""

from slayer.orchestrator.graph import build_pipeline_graph, run_pipeline
from slayer.orchestrator.state import PipelineState, build_initial_state

__all__ = [
    "build_pipeline_graph",
    "run_pipeline",
    "PipelineState",
    "build_initial_state",
]
