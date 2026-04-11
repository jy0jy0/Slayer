"""Resume Optimizer ReAct Agent.

LLM autonomously evaluates, decides optimization strategy, and iterates.
"""

from __future__ import annotations

import json
import logging
from typing import Any, Callable, Optional

from langgraph.prebuilt import create_react_agent

from slayer.agents.resume_optimizer.tools import evaluate_ats, optimize_blocks, analyze_optimization_impact
from slayer.llm import get_chat_model, parse_agent_json
from slayer.schemas import (
    BlockChange,
    BlockType,
    ResumeBlock,
    ResumeOptimizationInput,
    ResumeOptimizationOutput,
    parsed_resume_to_blocks,
)
from slayer.ui.events import EventType

logger = logging.getLogger(__name__)

# Applied at every ainvoke/astream_events call to cap ReAct loop length.
RUNTIME_CONFIG = {"recursion_limit": 15}

SYSTEM_PROMPT = """\
You are a resume optimization expert for Korean job seekers.

## Goal
Improve the resume's ATS score from the current score to the target ({target_score}/100).
Maximum {max_iterations} evaluation-optimization cycles allowed.

## Available tools
- evaluate_ats: Evaluate current ATS score of resume blocks against JD
- optimize_blocks: Apply optimization strategies (keyword insertion, quantification, reordering)
- analyze_optimization_impact: Analyze which changes had most impact and whether further optimization is worthwhile

## Your autonomy
You decide the strategy:
- Evaluate first to understand gaps, then optimize targeted weaknesses
- After optimization, re-evaluate using the OPTIMIZED blocks (not the original!)
- Use impact analysis to refine your approach if improvement is insufficient
- Stop early if target reached OR if diminishing returns detected
- If a specific dimension (keywords, experience, etc.) is weak, focus optimization there

## CRITICAL
After calling optimize_blocks, use the returned optimized_blocks as input to the next evaluate_ats call.
Do NOT re-evaluate the original blocks — that discards your optimization work.

## Final output
Return JSON:
{{
  "final_ats_score": <number>,
  "score_improvement": <number>,
  "iterations_used": <number>,
  "optimization_summary": "Korean summary of what was done and why",
  "optimized_blocks": [<final optimized blocks>],
  "changes": [<all changes across iterations>]
}}
"""

TOOLS = [evaluate_ats, optimize_blocks, analyze_optimization_impact]


def build_resume_optimizer_agent(target_score: float = 80, max_iterations: int = 3):
    """Build the ReAct agent graph."""
    model = get_chat_model("gpt-4o-mini")
    prompt = SYSTEM_PROMPT.format(target_score=target_score, max_iterations=max_iterations)
    return create_react_agent(model, TOOLS, prompt=prompt)


def should_continue(state) -> str:
    """For backward compatibility with tests."""
    if state.get("current_score", 0) >= state.get("target_ats_score", 80):
        return "done"
    if state.get("iteration", 0) >= state.get("max_iterations", 3):
        return "done"
    return "continue"



TOOL_LABELS = {
    "evaluate_ats": ("📊", "Evaluating ATS score"),
    "optimize_blocks": ("✨", "Optimizing resume blocks"),
    "analyze_optimization_impact": ("🔬", "Analyzing optimization impact"),
}


async def optimize_resume_streaming(
    input_data: ResumeOptimizationInput,
    on_event: Optional[Callable[[EventType, dict[str, Any]], None]] = None,
) -> ResumeOptimizationOutput:
    """Run resume optimization agent with streaming events."""
    logger.info("Resume optimizer agent started (target=%.0f, max_iter=%d)",
                input_data.target_ats_score, input_data.max_iterations)

    blocks = parsed_resume_to_blocks(input_data.parsed_resume)
    blocks_json = json.dumps([b.model_dump() for b in blocks], ensure_ascii=False, indent=2)
    jd_json = input_data.jd.model_dump_json(indent=2)

    agent = build_resume_optimizer_agent(input_data.target_ats_score, input_data.max_iterations)

    user_msg = f"""Optimize this resume to reach ATS score {input_data.target_ats_score}.

Current match result: ATS score = {input_data.match_result.ats_score}
Weaknesses: {json.dumps(input_data.match_result.weaknesses, ensure_ascii=False)}
Missing keywords: {json.dumps(input_data.match_result.missing_keywords, ensure_ascii=False)}

Resume blocks JSON:
{blocks_json}

JD JSON:
{jd_json}"""

    input_msg = {"messages": [{"role": "user", "content": user_msg}]}
    content = ""

    async for event in agent.astream_events(input_msg, version="v2", config=RUNTIME_CONFIG):
        kind = event.get("event", "")
        if kind == "on_chat_model_start" and on_event:
            on_event(EventType.THINKING, {"message": "Agent deciding next action..."})
        elif kind == "on_tool_start" and on_event:
            tool_name = event.get("name", "")
            icon, label = TOOL_LABELS.get(tool_name, ("🔧", tool_name))
            on_event(EventType.TOOL_CALL, {"tool": tool_name, "icon": icon, "label": label})
        elif kind == "on_tool_end" and on_event:
            tool_name = event.get("name", "")
            output = str(event.get("data", {}).get("output", ""))
            # Extract score if evaluate_ats
            summary = ""
            if tool_name == "evaluate_ats":
                try:
                    d = json.loads(output)
                    summary = f"ATS Score: {d.get('ats_score', '?')}/100"
                except (json.JSONDecodeError, TypeError):
                    summary = output[:80]
            else:
                try:
                    d = json.loads(output)
                    changes = d.get("changes", [])
                    summary = f"{len(changes)} changes applied"
                except (json.JSONDecodeError, TypeError):
                    summary = output[:80]
            on_event(EventType.TOOL_RESULT, {"tool": tool_name, "summary": summary})
        elif kind == "on_chat_model_end":
            output = event.get("data", {}).get("output", None)
            if output and hasattr(output, "content") and output.content:
                content = output.content

    if not content:
        try:
            result = await agent.ainvoke(input_msg, config=RUNTIME_CONFIG)
            messages = result.get("messages", [])
            if not messages:
                raise ValueError("Agent produced no output")
            final_message = messages[-1]
            content = final_message.content if hasattr(final_message, "content") else str(final_message)
        except Exception as e:
            logger.error("Fallback invocation failed: %s", e)
            content = ""

    if on_event:
        on_event(EventType.DONE, {"message": "Optimization complete"})

    try:
        data = json.loads(parse_agent_json(content))

        # Parse optimized blocks from agent output
        raw_blocks = data.get("optimized_blocks")
        if not raw_blocks:
            logger.warning("No optimized_blocks in agent output — using original blocks")
            final_blocks = blocks
        elif not isinstance(raw_blocks, list):
            logger.warning("optimized_blocks is not a list (%s) — using original blocks", type(raw_blocks))
            final_blocks = blocks
        else:
            try:
                final_blocks = [ResumeBlock(**b) for b in raw_blocks]
                logger.info("Parsed %d optimized blocks from agent output", len(final_blocks))
            except Exception as e:
                logger.warning("Failed to parse optimized blocks: %s — using original", e)
                final_blocks = blocks

        raw_changes = data.get("changes", [])
        parsed_changes = []
        for c in raw_changes:
            try:
                parsed_changes.append(BlockChange(**c))
            except Exception:
                continue

        return ResumeOptimizationOutput(
            optimized_blocks=final_blocks,
            final_ats_score=data.get("final_ats_score", input_data.match_result.ats_score),
            score_improvement=data.get("score_improvement", 0),
            changes=parsed_changes,
            iterations_used=data.get("iterations_used", 1),
            optimization_summary=data.get("optimization_summary", ""),
        )
    except (json.JSONDecodeError, ValueError) as e:
        logger.error("Failed to parse optimizer response: %s", e)
        return ResumeOptimizationOutput(
            optimized_blocks=blocks,
            final_ats_score=input_data.match_result.ats_score,
            score_improvement=0,
            iterations_used=0,
            optimization_summary=f"Parse error: {content[:200]}",
        )


async def optimize_resume(input_data: ResumeOptimizationInput) -> ResumeOptimizationOutput:
    """Run resume optimization agent (non-streaming, backward compatible)."""
    return await optimize_resume_streaming(input_data)


async def _optimize_resume_invoke(input_data: ResumeOptimizationInput) -> ResumeOptimizationOutput:
    """Fallback invoke version."""
    blocks = parsed_resume_to_blocks(input_data.parsed_resume)
    blocks_json = json.dumps([b.model_dump() for b in blocks], ensure_ascii=False, indent=2)
    jd_json = input_data.jd.model_dump_json(indent=2)
    agent = build_resume_optimizer_agent(input_data.target_ats_score, input_data.max_iterations)
    user_msg = f"""Optimize this resume to reach ATS score {input_data.target_ats_score}.
Current match result: ATS score = {input_data.match_result.ats_score}
Weaknesses: {json.dumps(input_data.match_result.weaknesses, ensure_ascii=False)}
Missing keywords: {json.dumps(input_data.match_result.missing_keywords, ensure_ascii=False)}
Resume blocks JSON: {blocks_json}
JD JSON: {jd_json}"""

    result = await agent.ainvoke(
        {"messages": [{"role": "user", "content": user_msg}]},
        config=RUNTIME_CONFIG,
    )

    final_message = result["messages"][-1]
    content = final_message.content if hasattr(final_message, "content") else str(final_message)

    try:
        data = json.loads(parse_agent_json(content))

        # Parse optimized blocks from agent output
        raw_blocks = data.get("optimized_blocks")
        if not raw_blocks:
            logger.warning("No optimized_blocks in agent output — using original blocks")
            final_blocks = blocks
        elif not isinstance(raw_blocks, list):
            logger.warning("optimized_blocks is not a list (%s) — using original blocks", type(raw_blocks))
            final_blocks = blocks
        else:
            try:
                final_blocks = [ResumeBlock(**b) for b in raw_blocks]
                logger.info("Parsed %d optimized blocks from agent output", len(final_blocks))
            except Exception as e:
                logger.warning("Failed to parse optimized blocks: %s — using original", e)
                final_blocks = blocks

        raw_changes = data.get("changes", [])
        parsed_changes = []
        for c in raw_changes:
            try:
                parsed_changes.append(BlockChange(**c))
            except Exception:
                continue

        return ResumeOptimizationOutput(
            optimized_blocks=final_blocks,
            final_ats_score=data.get("final_ats_score", input_data.match_result.ats_score),
            score_improvement=data.get("score_improvement", 0),
            changes=parsed_changes,
            iterations_used=data.get("iterations_used", 1),
            optimization_summary=data.get("optimization_summary", ""),
        )
    except (json.JSONDecodeError, ValueError) as e:
        logger.error("Failed to parse optimizer response: %s", e)
        return ResumeOptimizationOutput(
            optimized_blocks=blocks,
            final_ats_score=input_data.match_result.ats_score,
            score_improvement=0,
            iterations_used=0,
            optimization_summary=f"Parse error: {content[:200]}",
        )
