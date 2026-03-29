"""Cover letter tools — @tool decorated for ReAct agent."""

from __future__ import annotations

import json

from langchain_core.tools import tool

from slayer.llm import get_default_provider


@tool
def generate_draft(resume_json: str, jd_json: str, company_json: str, match_json: str) -> str:
    """Generate an initial cover letter draft.

    Args:
        resume_json: JSON string of parsed resume
        jd_json: JSON string of job description
        company_json: JSON string of company research output
        match_json: JSON string of match result

    Returns:
        JSON with cover_letter text and key_points list.
    """
    provider = get_default_provider()
    prompt = f"""Write a tailored cover letter in Korean (800-1200 chars).
Align resume strengths to JD requirements. Reference company research. Address gaps constructively.

Return JSON: {{"cover_letter": "full text in Korean", "key_points": ["3-5 key selling points"]}}

## JD: {jd_json}
## Resume: {resume_json}
## Company Research: {company_json}
## Match Analysis: {match_json}"""
    return provider.generate_json(prompt, system_message="Cover letter expert. JSON only.")


@tool
def review_and_refine(draft: str, jd_json: str) -> str:
    """Review and improve a cover letter draft.

    Args:
        draft: The current cover letter text
        jd_json: JSON string of job description for keyword reference

    Returns:
        JSON with refined_letter, key_points, and improvements list.
    """
    provider = get_default_provider()
    prompt = f"""Review and improve this cover letter. Check: keyword coverage, specificity, tone, flow, grammar.

Return JSON: {{"refined_letter": "improved text", "key_points": ["key points"], "improvements": ["what was improved"]}}

## JD skills/requirements: {jd_json}
## Draft: {draft}"""
    return provider.generate_json(prompt, system_message="Cover letter reviewer. JSON only.")


@tool
def compute_stats(cover_letter: str, jd_skills_json: str) -> str:
    """Compute cover letter statistics: word count and keyword coverage.

    Args:
        cover_letter: The cover letter text
        jd_skills_json: JSON string of JD skills list

    Returns:
        JSON with word_count and keyword_coverage (0-1).
    """
    skills = json.loads(jd_skills_json) if jd_skills_json else []
    word_count = len(cover_letter)
    if not skills:
        return json.dumps({"word_count": word_count, "keyword_coverage": 0.0})
    letter_lower = cover_letter.lower()
    matched = sum(1 for s in skills if s.lower() in letter_lower)
    coverage = min(matched / len(skills), 1.0)
    return json.dumps({"word_count": word_count, "keyword_coverage": round(coverage, 3)})
