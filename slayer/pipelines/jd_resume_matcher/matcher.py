"""JD-이력서 매칭 분석 — ReAct Agent.

NOTE: 현지님 프로덕션 구현으로 교체 가능
"""
from __future__ import annotations

import json
import logging
from typing import Callable, Optional

from langchain_core.tools import tool
from langgraph.prebuilt import create_react_agent

from slayer.llm import get_chat_model, get_default_provider, parse_agent_json
from slayer.schemas import JDSchema, MatchResult, ParsedResume

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════
# Tools
# ═══════════════════════════════════════════════════


@tool
def analyze_keywords(
    jd_skills_json: str,
    resume_skills_json: str,
    jd_requirements_json: str,
    resume_experiences_json: str,
) -> str:
    """Analyze keyword overlap between JD and resume.

    Args:
        jd_skills_json: JSON list of JD skill keywords
        resume_skills_json: JSON list of resume skill keywords
        jd_requirements_json: JSON of JD requirements (required/preferred)
        resume_experiences_json: JSON list of resume experience items

    Returns:
        JSON with matched_keywords, missing_keywords, coverage_ratio, and analysis.
    """
    provider = get_default_provider()
    prompt = f"""Analyze keyword overlap between this JD and resume.

Return JSON:
{{"matched_keywords": ["..."], "missing_keywords": ["..."], "coverage_ratio": 0.0-1.0, "keyword_analysis": "2-3 sentence summary"}}

## JD Skills: {jd_skills_json}
## JD Requirements: {jd_requirements_json}
## Resume Skills: {resume_skills_json}
## Resume Experiences: {resume_experiences_json}"""
    return provider.generate_json(prompt, system_message="ATS keyword analyst. JSON only.")


@tool
def assess_experience_fit(
    jd_requirements_json: str,
    jd_responsibilities_json: str,
    resume_experiences_json: str,
) -> str:
    """Assess how well the candidate's experience aligns with JD requirements and responsibilities.

    Args:
        jd_requirements_json: JSON of JD requirements (required/preferred)
        jd_responsibilities_json: JSON list of JD responsibilities (actual work content)
        resume_experiences_json: JSON list of resume experience items

    Returns:
        JSON with experience_score (0-100), strengths, weaknesses, and fit_summary.
    """
    provider = get_default_provider()
    prompt = f"""Assess experience alignment between JD and resume.

Use both requirements (qualifications) AND responsibilities (actual work) to evaluate fit.
Responsibilities reveal the real depth and domain of work expected.

Return JSON:
{{"experience_score": 0-100, "strengths": ["3-5 strengths"], "weaknesses": ["3-5 weaknesses"], "fit_summary": "2-3 sentence summary"}}

## JD Requirements: {jd_requirements_json}
## JD Responsibilities: {jd_responsibilities_json}
## Resume Experiences: {resume_experiences_json}"""
    return provider.generate_json(prompt, system_message="Experience fit assessor. JSON only.")


@tool
def identify_strategic_gaps(
    keyword_analysis_json: str,
    experience_analysis_json: str,
) -> str:
    """Synthesize keyword and experience analyses into a final ATS assessment.

    Args:
        keyword_analysis_json: JSON output from analyze_keywords
        experience_analysis_json: JSON output from assess_experience_fit

    Returns:
        JSON with ats_score, score_breakdown, gap_summary, and strategic_recommendations.
    """
    provider = get_default_provider()
    prompt = f"""Synthesize these analyses into a final ATS matching assessment.

ATS score weights:
- ats_simulation: 0.30
- keywords: 0.25
- experience: 0.20
- industry_specific: 0.15
- content: 0.05
- format: 0.03
- errors: 0.02

Return JSON:
{{"ats_score": 0-100, "score_breakdown": {{"ats_simulation": ..., "keywords": ..., "experience": ..., "industry_specific": ..., "content": ..., "format": ..., "errors": ...}}, "gap_summary": "종합 갭 분석 (2-3문장)", "strategic_recommendations": ["1-3 strategic suggestions"]}}

## Keyword Analysis: {keyword_analysis_json}
## Experience Analysis: {experience_analysis_json}"""
    return provider.generate_json(prompt, system_message="ATS 전문가. JSON only.")


MATCH_TOOLS = [analyze_keywords, assess_experience_fit, identify_strategic_gaps]

MATCH_TOOL_LABELS = {
    "analyze_keywords": ("🔑", "Analyzing keyword overlap"),
    "assess_experience_fit": ("💼", "Assessing experience fit"),
    "identify_strategic_gaps": ("🎯", "Identifying strategic gaps"),
}


# ═══════════════════════════════════════════════════
# System Prompt
# ═══════════════════════════════════════════════════

MATCH_SYSTEM_PROMPT = """\
You are an ATS (Applicant Tracking System) expert analyzing JD-resume fit.

## Goal
Produce a comprehensive match analysis with an accurate ATS score.
You decide the analysis depth based on the complexity of the JD and resume.

## Available tools
- analyze_keywords: Compare JD skills/requirements against resume skills/experiences
- assess_experience_fit: Evaluate how well experience aligns with JD requirements
- identify_strategic_gaps: Synthesize analyses into final ATS score and gap summary

## Your autonomy
- Start with analyze_keywords to understand skill overlap
- Then assess_experience_fit for deeper alignment analysis
- Finally identify_strategic_gaps to produce the ATS score
- For simple JDs, you may skip detailed experience assessment

## Final output
Return JSON:
{
  "ats_score": 0-100,
  "score_breakdown": {"ats_simulation": ..., "keywords": ..., "experience": ..., "industry_specific": ..., "content": ..., "format": ..., "errors": ...},
  "matched_keywords": ["matched keyword list"],
  "missing_keywords": ["missing keyword list"],
  "strengths": ["3-5 strengths"],
  "weaknesses": ["3-5 weaknesses"],
  "gap_summary": "종합 갭 분석 요약 (2-3문장)"
}
"""


# ═══════════════════════════════════════════════════
# Agent Builder
# ═══════════════════════════════════════════════════


def build_matcher_agent():
    """Build the ReAct agent graph for JD-resume matching."""
    model = get_chat_model("gpt-4o-mini")
    return create_react_agent(model, MATCH_TOOLS, prompt=MATCH_SYSTEM_PROMPT)


# ═══════════════════════════════════════════════════
# Helpers
# ═══════════════════════════════════════════════════




# ═══════════════════════════════════════════════════
# Main Entry Point
# ═══════════════════════════════════════════════════


async def match_jd_resume(
    jd: JDSchema,
    resume: ParsedResume,
    on_event: Optional[Callable] = None,
) -> MatchResult:
    """JD와 이력서를 매칭 분석하여 MatchResult를 반환.

    Args:
        jd: Parsed job description
        resume: Parsed resume
        on_event: Optional callback for streaming UI events

    Returns:
        MatchResult with ATS score and detailed analysis.
    """
    logger.info("JD-Resume matcher agent started (streaming)")
    agent = build_matcher_agent()

    jd_json = jd.model_dump_json(indent=2)
    resume_json = resume.model_dump_json(indent=2)
    skills_json = json.dumps(jd.skills, ensure_ascii=False)
    requirements_json = jd.requirements.model_dump_json(indent=2)
    responsibilities_json = json.dumps(jd.responsibilities, ensure_ascii=False, indent=2)
    experiences_json = json.dumps(
        [e.model_dump() for e in resume.experiences], ensure_ascii=False, indent=2
    )
    resume_skills_json = json.dumps(resume.skills, ensure_ascii=False)

    user_msg = f"""Analyze the match between this JD and resume.

JD: {jd_json}
Resume: {resume_json}
JD Skills (extracted): {skills_json}
JD Requirements: {requirements_json}
JD Responsibilities: {responsibilities_json}
Resume Skills: {resume_skills_json}
Resume Experiences: {experiences_json}"""

    input_msg = {"messages": [{"role": "user", "content": user_msg}]}
    content = ""

    async for event in agent.astream_events(input_msg, version="v2"):
        kind = event.get("event", "")
        if kind == "on_chat_model_start" and on_event:
            on_event("thinking", {"message": "Agent deciding next action..."})
        elif kind == "on_tool_start" and on_event:
            tool_name = event.get("name", "")
            icon, label = MATCH_TOOL_LABELS.get(tool_name, ("🔧", tool_name))
            on_event("tool_call", {"tool": tool_name, "icon": icon, "label": label})
        elif kind == "on_tool_end" and on_event:
            tool_name = event.get("name", "")
            output = str(event.get("data", {}).get("output", ""))
            if tool_name == "analyze_keywords":
                try:
                    d = json.loads(output)
                    ratio = d.get("coverage_ratio", 0)
                    summary = f"Keyword coverage: {ratio:.0%}"
                except (json.JSONDecodeError, TypeError):
                    summary = "Keywords analyzed"
            elif tool_name == "assess_experience_fit":
                try:
                    d = json.loads(output)
                    score = d.get("experience_score", "?")
                    summary = f"Experience fit: {score}/100"
                except (json.JSONDecodeError, TypeError):
                    summary = "Experience assessed"
            elif tool_name == "identify_strategic_gaps":
                try:
                    d = json.loads(output)
                    ats = d.get("ats_score", "?")
                    summary = f"ATS score: {ats}/100"
                except (json.JSONDecodeError, TypeError):
                    summary = "Gaps identified"
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
        on_event("done", {"message": "Match analysis complete"})

    try:
        data = json.loads(parse_agent_json(content))
        return MatchResult(
            ats_score=float(data.get("ats_score", 0)),
            score_breakdown=data.get("score_breakdown", {}),
            matched_keywords=data.get("matched_keywords", []),
            missing_keywords=data.get("missing_keywords", []),
            strengths=data.get("strengths", []),
            weaknesses=data.get("weaknesses", []),
            gap_summary=data.get("gap_summary", ""),
        )
    except (json.JSONDecodeError, ValueError, KeyError) as e:
        logger.error("Failed to parse matcher response: %s", e)
        return MatchResult(
            ats_score=0.0,
            gap_summary=f"Parse error: {e}. Raw: {content[:500]}",
        )


# ═══════════════════════════════════════════════════
# Mock (테스트용)
# ═══════════════════════════════════════════════════


def create_mock_match_result() -> MatchResult:
    """테스트용 목 데이터."""
    return MatchResult(
        ats_score=62.0,
        score_breakdown={
            "ats_simulation": 18.0,
            "keywords": 15.0,
            "experience": 14.0,
            "industry_specific": 8.0,
            "content": 4.0,
            "format": 2.0,
            "errors": 1.0,
        },
        matched_keywords=["python", "fastapi", "docker", "postgresql", "git"],
        missing_keywords=["kubernetes", "aws", "terraform", "ci/cd", "monitoring"],
        strengths=[
            "Python 백엔드 개발 경험 풍부",
            "FastAPI 프로젝트 다수 수행",
            "데이터베이스 설계 경험",
        ],
        weaknesses=[
            "클라우드 인프라 경험 부족",
            "DevOps 관련 키워드 누락",
            "대규모 트래픽 처리 경험 미기재",
        ],
        gap_summary=(
            "백엔드 개발 핵심 역량은 갖추고 있으나, 클라우드/인프라 관련 경험이 "
            "JD 요구사항 대비 부족합니다. kubernetes, AWS, CI/CD 파이프라인 경험을 "
            "보강하면 매칭률이 크게 향상될 것입니다."
        ),
    )
