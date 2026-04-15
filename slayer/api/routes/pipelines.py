"""Pipeline API endpoints — AI 기능을 HTTP로 노출."""

from __future__ import annotations

import asyncio
import concurrent.futures
import json
import logging
import tempfile
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/pipelines", tags=["pipelines"])


def _run_sync(coro):
    """이미 이벤트 루프가 있어도 코루틴을 실행."""
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None
    if loop and loop.is_running():
        with concurrent.futures.ThreadPoolExecutor() as pool:
            return pool.submit(asyncio.run, coro).result()
    return asyncio.run(coro)


# ─── Company Research ─────────────────────────────────────────────────────────

class CompanyResearchRequest(BaseModel):
    company_name: str


@router.post("/company-research")
async def company_research(req: CompanyResearchRequest):
    """기업 리서치 에이전트 실행."""
    if not req.company_name.strip():
        raise HTTPException(status_code=400, detail="company_name이 비어있습니다.")
    try:
        from slayer.agents.company_research.agent import run_company_research_streaming
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            None,
            lambda: _run_sync(run_company_research_streaming(req.company_name.strip()))
        )
        return result.model_dump()
    except Exception as e:
        logger.error("Company research failed: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


# ─── JD Parse ────────────────────────────────────────────────────────────────

class JDParseRequest(BaseModel):
    url: str


@router.post("/jd/parse")
async def parse_jd(req: JDParseRequest):
    """JD URL 크롤링 + 파싱."""
    if not req.url.strip():
        raise HTTPException(status_code=400, detail="url이 비어있습니다.")
    try:
        from slayer.pipelines.jd_parser.scraper import scrape_jd
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            None,
            lambda: scrape_jd(req.url.strip())
        )
        return result.model_dump()
    except Exception as e:
        logger.error("JD parse failed: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


# ─── JD-Resume Match ─────────────────────────────────────────────────────────

class MatchRequest(BaseModel):
    jd: dict[str, Any]
    resume: dict[str, Any]


@router.post("/match")
async def match_jd_resume(req: MatchRequest):
    """JD ↔ 이력서 ATS 매칭 분석."""
    try:
        from slayer.pipelines.jd_resume_matcher import match_jd_resume as _match
        from slayer.schemas import JDSchema, ParsedResume

        jd = JDSchema(**req.jd)
        resume = ParsedResume(**req.resume)
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            None,
            lambda: _run_sync(_match(jd, resume))
        )
        return result.model_dump()
    except Exception as e:
        logger.error("Match failed: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


# ─── Resume Optimize ─────────────────────────────────────────────────────────

class OptimizeRequest(BaseModel):
    parsed_resume: dict[str, Any]
    jd: dict[str, Any]
    match_result: dict[str, Any]
    target_ats_score: float = 80.0
    max_iterations: int = 3


@router.post("/optimize")
async def optimize_resume(req: OptimizeRequest):
    """이력서 최적화 에이전트 실행."""
    try:
        from slayer.agents.resume_optimizer.agent import optimize_resume_streaming
        from slayer.schemas import JDSchema, MatchResult, ParsedResume, ResumeOptimizationInput

        resume = ParsedResume(**req.parsed_resume)
        jd = JDSchema(**req.jd)
        match_result = MatchResult(**req.match_result)
        input_data = ResumeOptimizationInput(
            parsed_resume=resume,
            jd=jd,
            match_result=match_result,
            target_ats_score=req.target_ats_score,
            max_iterations=req.max_iterations,
        )
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            None,
            lambda: _run_sync(optimize_resume_streaming(input_data))
        )
        return result.model_dump()
    except Exception as e:
        logger.error("Optimize failed: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


# ─── Cover Letter ─────────────────────────────────────────────────────────────

class CoverLetterRequest(BaseModel):
    parsed_resume: dict[str, Any]
    jd: dict[str, Any]
    company_research: dict[str, Any] | None = None
    match_result: dict[str, Any] | None = None


@router.post("/cover-letter")
async def generate_cover_letter(req: CoverLetterRequest):
    """자소서 생성 에이전트 실행."""
    try:
        from slayer.agents.cover_letter.agent import generate_cover_letter_streaming
        from slayer.schemas import (
            CoverLetterInput, CompanyResearchOutput, JDSchema, MatchResult, ParsedResume
        )

        resume = ParsedResume(**req.parsed_resume)
        jd = JDSchema(**req.jd)
        company = CompanyResearchOutput(**req.company_research) if req.company_research else None
        match_result = MatchResult(**req.match_result) if req.match_result else None

        input_data = CoverLetterInput(
            parsed_resume=resume,
            jd=jd,
            company_research=company,
            match_result=match_result,
        )
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            None,
            lambda: _run_sync(generate_cover_letter_streaming(input_data))
        )
        return result.model_dump()
    except Exception as e:
        logger.error("Cover letter failed: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


# ─── Interview Prep ───────────────────────────────────────────────────────────

class InterviewRequest(BaseModel):
    jd: dict[str, Any]
    resume: dict[str, Any]
    company_research: dict[str, Any] | None = None
    match_result: dict[str, Any] | None = None
    questions_per_category: int = 3


@router.post("/interview")
async def generate_interview_questions(req: InterviewRequest):
    """면접 질문 생성."""
    try:
        from slayer.pipelines.interview_questions import generate_interview_questions as _gen
        from slayer.schemas import (
            CompanyResearchOutput, InterviewQuestionsInput, JDSchema, MatchResult, ParsedResume
        )

        jd = JDSchema(**req.jd)
        resume = ParsedResume(**req.resume)
        company = CompanyResearchOutput(**req.company_research) if req.company_research else None
        match_result = MatchResult(**req.match_result) if req.match_result else None

        input_data = InterviewQuestionsInput(
            jd=jd,
            resume=resume,
            company_research=company,
            match_result=match_result,
            questions_per_category=req.questions_per_category,
        )
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(None, _gen, input_data)
        return result.model_dump()
    except Exception as e:
        logger.error("Interview prep failed: %s", e)
        raise HTTPException(status_code=500, detail=str(e))
