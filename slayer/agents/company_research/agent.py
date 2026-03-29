"""Company Research ReAct Agent.

LLM autonomously decides which tools to call and in what order.
Uses LangGraph's create_react_agent with tool-calling.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime

from langgraph.prebuilt import create_react_agent

from slayer.agents.company_research.researcher import _dict_to_schema
from slayer.agents.company_research.tools import (
    get_corp_info,
    get_financial_info,
    search_news,
)
from slayer.llm import get_chat_model
from slayer.schemas import CompanyResearchOutput

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """\
You are a company research agent for Korean job seekers.

Your task: Research the given company using the available tools and produce a structured report.

## Available tools
- search_news: Search recent news about the company
- get_corp_info: Get basic corporate info (CEO, employees, industry, etc.) — also returns corp_reg_no (crno) needed for financial lookup
- get_financial_info: Get financial statements (requires crno from get_corp_info)

## Strategy
1. Start by getting corporate info (get_corp_info) — this gives you the crno needed for financials
2. In parallel or after, search for news (search_news)
3. If you got a crno, get financial info (get_financial_info)
4. If a tool returns empty or error, note it and move on — don't retry excessively

## Final output
After collecting enough data, produce your final answer as a JSON object with this structure:
{
  "company_name": "회사명",
  "company_name_en": "English name or null",
  "basic_info": {"industry": "...", "ceo": "...", "founded_date": "...", "employee_count": "...", "headquarters": "...", "business_registration_number": "...", "corp_registration_number": "...", "listing_info": "..."},
  "financial_info": {"revenue": "...", "operating_profit": "...", "net_income": "...", "total_assets": "...", "total_liabilities": "...", "capital": "...", "debt_ratio": "...", "fiscal_year": "..."} or null,
  "recent_news": [{"title": "...", "summary": "1-2 sentence summary", "source_url": "...", "published_date": "..."}],  // include ALL news from search results (up to 10)
  "summary": "200-400 character summary from a job seeker's perspective (Korean)"
}

Use ONLY data from tool results. Do not fabricate information. Set missing fields to null.
Write the summary in Korean.
"""

TOOLS = [search_news, get_corp_info, get_financial_info]


def build_company_research_agent():
    """Build the ReAct agent graph."""
    model = get_chat_model("gpt-4o-mini")
    return create_react_agent(model, TOOLS, prompt=SYSTEM_PROMPT)


def _parse_final_content(content: str) -> str:
    """Extract JSON string from LLM response."""
    if "```json" in content:
        return content.split("```json")[1].split("```")[0].strip()
    if "```" in content:
        return content.split("```")[1].split("```")[0].strip()
    if content.strip().startswith("{"):
        return content.strip()
    start = content.index("{")
    end = content.rindex("}") + 1
    return content[start:end]


async def run_company_research_streaming(company_name: str, on_event=None):
    """Run company research agent with streaming events.

    Args:
        company_name: Company to research.
        on_event: Callback(event_type, data) called for each agent step.
            event_type: "thinking" | "tool_call" | "tool_result" | "done"
            data: dict with relevant info.

    Returns:
        CompanyResearchOutput
    """
    logger.info("Company research agent started (streaming): %s", company_name)
    agent = build_company_research_agent()

    input_msg = {"messages": [{"role": "user", "content": f"Research the company: {company_name}"}]}
    content = ""

    async for event in agent.astream_events(input_msg, version="v2"):
        kind = event.get("event", "")

        if kind == "on_chat_model_start":
            if on_event:
                on_event("thinking", {"message": "Agent is thinking..."})

        elif kind == "on_tool_start":
            tool_name = event.get("name", "unknown")
            tool_input = event.get("data", {}).get("input", {})
            if on_event:
                on_event("tool_call", {"tool": tool_name, "input": tool_input})

        elif kind == "on_tool_end":
            tool_name = event.get("name", "unknown")
            output = event.get("data", {}).get("output", "")
            # Summarize output for display
            output_str = str(output)
            summary = output_str[:200] + "..." if len(output_str) > 200 else output_str
            if on_event:
                on_event("tool_result", {"tool": tool_name, "summary": summary})

        elif kind == "on_chat_model_end":
            output = event.get("data", {}).get("output", None)
            if output and hasattr(output, "content"):
                content = output.content

    if not content:
        # Fallback: run non-streaming
        result = await agent.ainvoke(input_msg)
        final_message = result["messages"][-1]
        content = final_message.content if hasattr(final_message, "content") else str(final_message)

    if on_event:
        on_event("done", {"message": "Generating report..."})

    logger.info("Agent completed. Parsing result...")

    try:
        json_str = _parse_final_content(content)
        data = json.loads(json_str)
        data["data_sources"] = ["naver_news", "corp_info", "financial_info"]
        data["researched_at"] = datetime.now().isoformat()
        return _dict_to_schema(data)
    except (json.JSONDecodeError, ValueError) as e:
        logger.error("Failed to parse agent response: %s", e)
        return CompanyResearchOutput(
            company_name=company_name,
            summary=content[:500],
            researched_at=datetime.now().isoformat(),
        )


async def run_company_research(company_name: str) -> CompanyResearchOutput:
    """Run company research agent (non-streaming, backward compatible)."""
    return await run_company_research_streaming(company_name)


async def _run_company_research_invoke(company_name: str) -> CompanyResearchOutput:
    """Run using ainvoke (fallback)."""
    logger.info("Company research agent started (invoke): %s", company_name)
    agent = build_company_research_agent()
    result = await agent.ainvoke(
        {"messages": [{"role": "user", "content": f"Research the company: {company_name}"}]}
    )
    final_message = result["messages"][-1]
    content = final_message.content if hasattr(final_message, "content") else str(final_message)
    try:
        json_str = _parse_final_content(content)
        data = json.loads(json_str)
        data["data_sources"] = ["naver_news", "corp_info", "financial_info"]
        data["researched_at"] = datetime.now().isoformat()
        return _dict_to_schema(data)

    except (json.JSONDecodeError, ValueError) as e:
        logger.error("Failed to parse agent response: %s", e)
        logger.debug("Raw response: %s", content)
        return CompanyResearchOutput(
            company_name=company_name,
            summary=content[:500],
            researched_at=datetime.now().isoformat(),
        )
