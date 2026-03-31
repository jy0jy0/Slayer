"""Resume optimizer tools — @tool decorated for ReAct agent."""

from __future__ import annotations

from langchain_core.tools import tool

from slayer.llm import get_default_provider


@tool
def evaluate_ats(resume_blocks_json: str, jd_json: str) -> str:
    """Evaluate the current ATS score of resume blocks against a job description.

    Args:
        resume_blocks_json: JSON string of resume blocks array
        jd_json: JSON string of the job description (JDSchema)

    Returns:
        JSON with ats_score (0-100), score_breakdown, matched/missing keywords, strengths, weaknesses, gap_summary.
    """
    provider = get_default_provider()
    prompt = f"""You are an ATS scoring expert. Evaluate the resume against the JD.

ATS weights: ats_simulation(0.30), keywords(0.25), experience(0.20), industry_specific(0.15), content(0.05), format(0.03), errors(0.02)

Return JSON:
{{"ats_score": 0-100, "score_breakdown": {{"ats_simulation": ..., "keywords": ..., "experience": ..., "industry_specific": ..., "content": ..., "format": ..., "errors": ...}}, "matched_keywords": [...], "missing_keywords": [...], "strengths": [...], "weaknesses": [...], "gap_summary": "..."}}

## JD
{jd_json}

## Resume Blocks
{resume_blocks_json}"""
    return provider.generate_json(prompt, system_message="ATS scoring expert. JSON only.")


@tool
def optimize_blocks(resume_blocks_json: str, jd_json: str, weaknesses_json: str, missing_keywords_json: str) -> str:
    """Optimize resume blocks to improve ATS score.

    Args:
        resume_blocks_json: JSON string of current resume blocks
        jd_json: JSON string of the job description
        weaknesses_json: JSON string of current weaknesses list
        missing_keywords_json: JSON string of missing keywords list

    Returns:
        JSON with optimized_blocks array and changes array.
    """
    provider = get_default_provider()
    prompt = f"""You are a resume optimization expert. Optimize blocks to improve ATS score.
Strategies: keyword insertion, quantify achievements, reorder blocks, reduce irrelevant content.

Return JSON:
{{"optimized_blocks": [{{"block_type": "...", "order": 0, "content": {{...}}, "relevance_score": 0.0-1.0}}], "changes": [{{"block_type": "...", "original_order": 0, "new_order": 0, "change_type": "enhance|reorder|add_keyword|quantify", "before": "...", "after": "...", "reason": "..."}}]}}

## JD
{jd_json}

## Weaknesses: {weaknesses_json}
## Missing Keywords: {missing_keywords_json}
## Current Blocks
{resume_blocks_json}"""
    return provider.generate_json(prompt, system_message="Resume optimization expert. JSON only.")


@tool
def analyze_optimization_impact(before_score: str, after_score: str, changes_json: str) -> str:
    """Analyze which optimization changes had the most impact on ATS score.

    Use after an optimize+re-evaluate cycle to understand what worked.

    Args:
        before_score: ATS score before optimization (e.g. "62.0")
        after_score: ATS score after optimization (e.g. "71.0")
        changes_json: JSON string of changes array from optimize_blocks

    Returns:
        JSON with score_delta, effective_changes, diminishing_returns (bool),
        suggested_focus for next iteration, and confidence (0.0-1.0).
    """
    provider = get_default_provider()
    prompt = f"""Analyze optimization impact.
Before: {before_score}, After: {after_score}
Changes: {changes_json}

Return JSON:
{{"score_delta": <number>, "effective_changes": ["..."], "diminishing_returns": true/false, "suggested_focus": "...", "confidence": 0.0-1.0}}"""
    return provider.generate_json(prompt, system_message="ATS optimization analyst. JSON only.")
