"""Cover Letter ReAct Agent.

LLM autonomously drafts, reviews, and refines the cover letter.
"""

from __future__ import annotations

import json
import logging

from langgraph.prebuilt import create_react_agent

from slayer.agents.cover_letter.tools import compute_stats, generate_draft, review_and_refine, evaluate_draft_quality
from slayer.llm import get_chat_model, parse_agent_json
from slayer.schemas import CoverLetterInput, CoverLetterOutput

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """\
You are a cover letter writing expert for Korean job seekers.

## Goal
Generate the best possible cover letter that maximizes the candidate's chances.
You decide when the letter is good enough based on quality metrics.

## Available tools
- generate_draft: Create initial draft from resume, JD, company research, match result
- review_and_refine: Improve an existing draft
- compute_stats: Get word count and keyword coverage ratio
- evaluate_draft_quality: Multi-dimensional quality assessment (keywords, tone, structure, specificity, company_alignment)

## Your autonomy
- Generate a draft, then assess its quality with evaluate_draft_quality
- If any dimension scores below 70, refine with targeted improvements
- Use compute_stats to verify keyword coverage (aim for 50%+)
- You may refine multiple times, but stop when evaluate_draft_quality returns is_ready: true
- If company research reveals key themes, ensure the letter references them

## Quality standards
- Length: 800-1200 characters (Korean)
- Keyword coverage: >= 50% of JD skills mentioned naturally
- All quality dimensions >= 70/100

## Final output
Return JSON:
{
  "cover_letter": "final cover letter text in Korean",
  "key_points": ["3-5 strategic selling points"],
  "jd_keyword_coverage": 0.0-1.0,
  "word_count": <number>
}
"""

TOOLS = [generate_draft, review_and_refine, compute_stats, evaluate_draft_quality]


def build_cover_letter_agent():
    """Build the ReAct agent graph."""
    model = get_chat_model("gpt-4o-mini")
    return create_react_agent(model, TOOLS, prompt=SYSTEM_PROMPT)



TOOL_LABELS = {
    "generate_draft": ("📝", "Drafting cover letter"),
    "review_and_refine": ("🔍", "Reviewing & refining"),
    "compute_stats": ("📊", "Computing statistics"),
    "evaluate_draft_quality": ("🎯", "Evaluating quality dimensions"),
}


async def generate_cover_letter_streaming(input_data: CoverLetterInput, on_event=None) -> CoverLetterOutput:
    """Run cover letter agent with streaming events."""
    logger.info("Cover letter agent started (streaming)")
    agent = build_cover_letter_agent()

    resume_json = input_data.parsed_resume.model_dump_json(indent=2)
    jd_json = input_data.jd.model_dump_json(indent=2)
    company_json = input_data.company_research.model_dump_json(indent=2)
    match_json = input_data.match_result.model_dump_json(indent=2)
    skills_json = json.dumps(input_data.jd.skills, ensure_ascii=False)

    user_msg = f"""Generate a tailored cover letter.

Resume: {resume_json}
JD: {jd_json}
Company Research: {company_json}
Match Result: {match_json}
JD Skills (for stats): {skills_json}"""

    input_msg = {"messages": [{"role": "user", "content": user_msg}]}
    content = ""

    async for event in agent.astream_events(input_msg, version="v2"):
        kind = event.get("event", "")
        if kind == "on_chat_model_start" and on_event:
            on_event("thinking", {"message": "Agent deciding next action..."})
        elif kind == "on_tool_start" and on_event:
            tool_name = event.get("name", "")
            icon, label = TOOL_LABELS.get(tool_name, ("🔧", tool_name))
            on_event("tool_call", {"tool": tool_name, "icon": icon, "label": label})
        elif kind == "on_tool_end" and on_event:
            tool_name = event.get("name", "")
            output = str(event.get("data", {}).get("output", ""))
            if tool_name == "generate_draft":
                try:
                    d = json.loads(output)
                    letter = d.get("cover_letter", "")
                    summary = f"Draft generated ({len(letter)} chars)"
                except (json.JSONDecodeError, TypeError):
                    summary = "Draft generated"
            elif tool_name == "review_and_refine":
                summary = "Letter refined & improved"
            elif tool_name == "compute_stats":
                try:
                    d = json.loads(output)
                    summary = f"Coverage: {d.get('keyword_coverage', 0):.0%}, Words: {d.get('word_count', '?')}"
                except (json.JSONDecodeError, TypeError):
                    summary = "Stats computed"
            elif tool_name == "evaluate_draft_quality":
                try:
                    d = json.loads(output)
                    score = d.get("overall_score", "?")
                    ready = d.get("is_ready", False)
                    weakest = d.get("weakest_dimension", "?")
                    summary = f"Score: {score}/100, Ready: {ready}, Weakest: {weakest}"
                except (json.JSONDecodeError, TypeError):
                    summary = "Quality evaluated"
            else:
                summary = output[:80]
            on_event("tool_result", {"tool": tool_name, "summary": summary})
        elif kind == "on_chat_model_end":
            output = event.get("data", {}).get("output", None)
            if output and hasattr(output, "content") and output.content:
                content = output.content

    if not content:
        try:
            result = await agent.ainvoke(input_msg)
            messages = result.get("messages", [])
            if not messages:
                raise ValueError("Agent produced no output")
            final_message = messages[-1]
            content = final_message.content if hasattr(final_message, "content") else str(final_message)
        except Exception as e:
            logger.error("Fallback invocation failed: %s", e)
            content = ""

    if on_event:
        on_event("done", {"message": "Cover letter complete"})

    try:
        data = json.loads(parse_agent_json(content))
        return CoverLetterOutput(
            cover_letter=data.get("cover_letter", ""),
            key_points=data.get("key_points", []),
            jd_keyword_coverage=float(data.get("jd_keyword_coverage", 0)),
            word_count=int(data.get("word_count", len(data.get("cover_letter", "")))),
        )
    except (json.JSONDecodeError, ValueError) as e:
        logger.error("Failed to parse cover letter response: %s", e)
        return CoverLetterOutput(
            cover_letter=content[:2000],
            key_points=[],
            jd_keyword_coverage=0.0,
            word_count=len(content),
        )


async def generate_cover_letter(input_data: CoverLetterInput) -> CoverLetterOutput:
    """Run cover letter agent (non-streaming, backward compatible)."""
    return await generate_cover_letter_streaming(input_data)
