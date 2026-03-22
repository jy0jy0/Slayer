"""schemas.py - Slayer 프로젝트 중앙 스키마 정의

DRAFT - 팀 리뷰 후 확정 (03/13 미팅 기반 초안)

모든 모듈 간 데이터 계약(contract)을 정의합니다.
각 기능 모듈에서 import하여 사용합니다.

사용 예시:
    from schemas import JDSchema, ParsedResume, MatchResult
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


# ═══════════════════════════════════════════════════
# Enums
# ═══════════════════════════════════════════════════


class BlockType(str, Enum):
    """이력서 블록 유형."""

    PERSONAL_INFO = "personal_info"
    SUMMARY = "summary"
    EXPERIENCE = "experience"
    PROJECT = "project"
    EDUCATION = "education"
    SKILLS = "skills"
    CERTIFICATION = "certification"
    PUBLICATION = "publication"
    AWARD = "award"
    OTHER = "other"


# ═══════════════════════════════════════════════════
# JD (채용공고) 스키마 — 현지님 TypedDict 호환
# ═══════════════════════════════════════════════════


class JDOverview(BaseModel):
    """채용공고 개요 정보."""

    employment_type: Optional[str] = None
    experience: Optional[str] = None
    education: Optional[str] = None
    salary: Optional[str] = None
    location: Optional[str] = None
    deadline: Optional[str] = None
    headcount: Optional[str] = None
    work_hours: Optional[str] = None


class JDRequirements(BaseModel):
    """채용 요구사항 (필수/우대)."""

    required: list[str] = Field(default_factory=list)
    preferred: list[str] = Field(default_factory=list)


class JDSchema(BaseModel):
    """채용공고 구조화 데이터.

    현지님(shinhyunji36)의 JD 파싱 Pipeline 출력과 1:1 호환.
    Discussion #6 (2026-03-13) 스키마 기준.
    """

    company: str
    title: str
    position: str
    overview: JDOverview = Field(default_factory=JDOverview)
    responsibilities: list[str] = Field(default_factory=list)
    requirements: JDRequirements = Field(default_factory=JDRequirements)
    skills: list[str] = Field(default_factory=list)
    benefits: list[str] = Field(default_factory=list)
    process: list[str] = Field(default_factory=list)
    notes: Optional[str] = None
    url: Optional[str] = None
    platform: Optional[str] = None


# ═══════════════════════════════════════════════════
# 이력서 파싱 결과 — 예신님 이력서 파싱 Pipeline 출력
# ═══════════════════════════════════════════════════


class PersonalInfo(BaseModel):
    """인적사항."""

    name: str
    email: Optional[str] = None
    phone: Optional[str] = None
    birth_year: Optional[int] = None
    links: list[str] = Field(default_factory=list)


class ExperienceItem(BaseModel):
    """경력 항목."""

    company: str
    position: str
    department: Optional[str] = None
    start_date: str  # "2022-03" 형식
    end_date: Optional[str] = None  # None = 재직중
    is_current: bool = False
    description: Optional[str] = None
    achievements: list[str] = Field(default_factory=list)


class ProjectItem(BaseModel):
    """프로젝트 항목."""

    name: str
    company: Optional[str] = None
    role: Optional[str] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    description: str = ""
    tech_stack: list[str] = Field(default_factory=list)
    achievements: list[str] = Field(default_factory=list)


class EducationItem(BaseModel):
    """학력 항목."""

    school: str
    major: Optional[str] = None
    degree: Optional[str] = None  # "학사", "석사", "박사"
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    is_current: bool = False


class CertificationItem(BaseModel):
    """자격증 항목."""

    name: str
    issuer: Optional[str] = None
    date: Optional[str] = None


class PublicationItem(BaseModel):
    """논문/발표 항목."""

    title: str
    venue: Optional[str] = None
    date: Optional[str] = None
    url: Optional[str] = None


class ParsedResume(BaseModel):
    """이력서 파싱 결과.

    예신님(yesinkim) 이력서 파싱 Pipeline의 출력 스키마.
    다양한 포맷(PDF, DOCX, MD, JSON, TXT)의 이력서를 파싱한 결과를
    통일된 구조로 제공합니다.
    """

    personal_info: PersonalInfo
    summary: Optional[str] = None
    experiences: list[ExperienceItem] = Field(default_factory=list)
    projects: list[ProjectItem] = Field(default_factory=list)
    education: list[EducationItem] = Field(default_factory=list)
    skills: list[str] = Field(default_factory=list)
    certifications: list[CertificationItem] = Field(default_factory=list)
    publications: list[PublicationItem] = Field(default_factory=list)
    total_years_experience: Optional[float] = None
    source_format: Optional[str] = None  # "pdf", "docx", "md", "json", "txt"


# ═══════════════════════════════════════════════════
# 이력서 블록 구조 — RESUME_RESEARCH.md 기반
# ═══════════════════════════════════════════════════


class ResumeBlock(BaseModel):
    """이력서의 단일 블록.

    이력서를 블록 단위로 분리하여 JD에 맞게 재배치할 수 있도록 합니다.
    """

    block_type: BlockType
    order: int
    content: dict  # 블록 타입별 내용 (유연성 위해 dict 사용)
    relevance_score: Optional[float] = Field(
        default=None, ge=0.0, le=1.0
    )  # JD 대비 관련성


def parsed_resume_to_blocks(resume: ParsedResume) -> list[ResumeBlock]:
    """ParsedResume을 블록 리스트로 변환 (최적화 Agent 입력용)."""
    blocks: list[ResumeBlock] = []
    order = 0

    # 인적사항
    blocks.append(
        ResumeBlock(
            block_type=BlockType.PERSONAL_INFO,
            order=order,
            content=resume.personal_info.model_dump(),
        )
    )

    # 요약
    if resume.summary:
        order += 1
        blocks.append(
            ResumeBlock(
                block_type=BlockType.SUMMARY,
                order=order,
                content={"text": resume.summary},
            )
        )

    # 경력
    for exp in resume.experiences:
        order += 1
        blocks.append(
            ResumeBlock(
                block_type=BlockType.EXPERIENCE,
                order=order,
                content=exp.model_dump(),
            )
        )

    # 프로젝트
    for proj in resume.projects:
        order += 1
        blocks.append(
            ResumeBlock(
                block_type=BlockType.PROJECT,
                order=order,
                content=proj.model_dump(),
            )
        )

    # 학력
    for edu in resume.education:
        order += 1
        blocks.append(
            ResumeBlock(
                block_type=BlockType.EDUCATION,
                order=order,
                content=edu.model_dump(),
            )
        )

    # 기술스택
    if resume.skills:
        order += 1
        blocks.append(
            ResumeBlock(
                block_type=BlockType.SKILLS,
                order=order,
                content={"items": resume.skills},
            )
        )

    # 자격증
    for cert in resume.certifications:
        order += 1
        blocks.append(
            ResumeBlock(
                block_type=BlockType.CERTIFICATION,
                order=order,
                content=cert.model_dump(),
            )
        )

    # 논문
    for pub in resume.publications:
        order += 1
        blocks.append(
            ResumeBlock(
                block_type=BlockType.PUBLICATION,
                order=order,
                content=pub.model_dump(),
            )
        )

    return blocks


# ═══════════════════════════════════════════════════
# JD-이력서 매칭 결과
# ═══════════════════════════════════════════════════


class MatchResult(BaseModel):
    """JD-이력서 매칭 결과.

    ATS 점수 산출 가중치 (RESUME_RESEARCH.md / JobPT 참고):
        ats_simulation: 0.30
        keywords: 0.25
        experience: 0.20
        industry_specific: 0.15
        content: 0.05
        format: 0.03
        errors: 0.02
    """

    ats_score: float = Field(ge=0, le=100)
    score_breakdown: dict[str, float] = Field(default_factory=dict)
    matched_keywords: list[str] = Field(default_factory=list)
    missing_keywords: list[str] = Field(default_factory=list)
    strengths: list[str] = Field(default_factory=list)
    weaknesses: list[str] = Field(default_factory=list)
    gap_summary: str = ""


# ═══════════════════════════════════════════════════
# 이력서 최적화 Agent — 지호 + 현지
# ═══════════════════════════════════════════════════


class ResumeOptimizationInput(BaseModel):
    """이력서 최적화 Agent 입력."""

    parsed_resume: ParsedResume
    jd: JDSchema
    match_result: MatchResult
    target_ats_score: float = Field(default=80.0, ge=0, le=100)
    max_iterations: int = Field(default=3, ge=1, le=10)


class BlockChange(BaseModel):
    """블록 단위 변경 사항."""

    block_type: BlockType
    original_order: int
    new_order: Optional[int] = None
    change_type: str  # "reorder", "enhance", "add_keyword", "quantify", "remove"
    before: Optional[str] = None
    after: Optional[str] = None
    reason: str = ""


class ResumeOptimizationOutput(BaseModel):
    """이력서 최적화 Agent 출력."""

    optimized_blocks: list[ResumeBlock]
    final_ats_score: float = Field(ge=0, le=100)
    score_improvement: float
    changes: list[BlockChange] = Field(default_factory=list)
    iterations_used: int
    optimization_summary: str = ""


# ═══════════════════════════════════════════════════
# 기업 리서치 — 기존 llm_client.py 출력 정형화
# ═══════════════════════════════════════════════════


class BasicInfo(BaseModel):
    """기업 기본정보."""

    industry: Optional[str] = None
    ceo: Optional[str] = None
    founded_date: Optional[str] = None
    employee_count: Optional[str] = None
    headquarters: Optional[str] = None
    business_registration_number: Optional[str] = None
    corp_registration_number: Optional[str] = None
    listing_info: Optional[str] = None


class FinancialInfo(BaseModel):
    """기업 재무정보."""

    revenue: Optional[str] = None
    operating_profit: Optional[str] = None
    net_income: Optional[str] = None
    total_assets: Optional[str] = None
    total_liabilities: Optional[str] = None
    capital: Optional[str] = None
    debt_ratio: Optional[str] = None
    fiscal_year: Optional[str] = None


class NewsItem(BaseModel):
    """뉴스 항목."""

    title: str
    summary: Optional[str] = None
    source_url: Optional[str] = None
    published_date: Optional[str] = None


class CompanyResearchOutput(BaseModel):
    """기업 리서치 Agent 출력.

    기존 company_research/llm_client.py의 JSON 구조를 Pydantic으로 정형화.
    """

    company_name: str
    company_name_en: Optional[str] = None
    basic_info: BasicInfo = Field(default_factory=BasicInfo)
    financial_info: Optional[FinancialInfo] = None
    recent_news: list[NewsItem] = Field(default_factory=list)
    summary: str = ""
    data_sources: list[str] = Field(default_factory=list)
    researched_at: str = ""


# ═══════════════════════════════════════════════════
# 자기소개서 생성 — 지호
# ═══════════════════════════════════════════════════


class CoverLetterInput(BaseModel):
    """자기소개서 생성 입력.

    JD + 이력서 + 기업 리서치 + 매칭 결과를 종합하여
    맞춤형 자기소개서를 생성합니다.
    """

    parsed_resume: ParsedResume
    jd: JDSchema
    company_research: CompanyResearchOutput
    match_result: MatchResult


class CoverLetterOutput(BaseModel):
    """자기소개서 생성 출력."""

    cover_letter: str
    key_points: list[str] = Field(default_factory=list)
    jd_keyword_coverage: float = Field(ge=0.0, le=1.0)
    word_count: int = 0
