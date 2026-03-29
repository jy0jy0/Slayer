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


class ApplicationStatus(str, Enum):
    """지원 상위 상태 (대시보드 필터용).

    상세 전형 단계는 ApplicationStage로 별도 관리.
    """

    SCRAPPED = "scrapped"
    REVIEWING = "reviewing"
    APPLIED = "applied"
    IN_PROGRESS = "in_progress"
    FINAL_PASS = "final_pass"
    REJECTED = "rejected"
    WITHDRAWN = "withdrawn"


class TriggerType(str, Enum):
    """상태 변경 트리거 유형."""

    EMAIL_DETECTED = "email_detected"
    USER_MANUAL = "user_manual"
    APPLY_ACTION = "apply_action"
    AGENT_AUTO = "agent_auto"


class GmailStatusType(str, Enum):
    """Gmail Monitor가 분류한 메일 유형."""

    PASS = "PASS"
    FAIL = "FAIL"
    INTERVIEW = "INTERVIEW"
    REJECT = "REJECT"


class StageStatus(str, Enum):
    """전형 단계 상태."""

    PENDING = "pending"
    PASSED = "passed"
    FAILED = "failed"


# ═══════════════════════════════════════════════════
# JD (채용공고) 스키마
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

    JD 파싱 Pipeline 출력과 1:1 호환.
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
# 이력서 파싱 결과
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

    이력서 파싱 Pipeline의 출력 스키마.
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
# 이력서 최적화 Agent
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
# 자기소개서 생성
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


# ═══════════════════════════════════════════════════
# 면접 질문 생성 — 현지
# ═══════════════════════════════════════════════════


class InterviewCategory(str, Enum):
    """면접 질문 카테고리."""

    TECHNICAL = "기술"
    EXPERIENCE = "경험"
    SITUATIONAL = "상황/행동"
    PERSONALITY = "인성"
    CULTURE_FIT = "컬처핏"
    COMPANY_KNOWLEDGE = "기업 이해도"


class InterviewQuestion(BaseModel):
    """면접 질문 항목."""

    category: InterviewCategory
    question: str
    intent: str   # 면접관이 이 질문을 하는 이유
    tip: str      # 답변 팁
    source: str   # 생성 근거 (e.g. "missing_keyword: Kubernetes", "company_news: 흑자전환")


class SampleAnswer(BaseModel):
    """면접 질문 예시 답변 (STAR 기법)."""

    question: str
    answer: str


class InterviewQuestionsInput(BaseModel):
    """면접 질문 생성 입력.

    jd, resume은 필수.
    company_research가 없으면 컬처핏·기업이해도 카테고리가 자동 제외됨.
    match_result가 없으면 상황/행동 카테고리가 자동 제외됨.
    """

    jd: JDSchema
    resume: ParsedResume
    company_research: Optional[CompanyResearchOutput] = None
    match_result: Optional[MatchResult] = None
    categories: Optional[list[InterviewCategory]] = None  # None이면 전체 생성
    questions_per_category: int = Field(default=3, ge=1, le=10)


class InterviewQuestionsOutput(BaseModel):
    """면접 질문 생성 출력."""

    questions: list[InterviewQuestion]
    sample_answers: list[SampleAnswer]
    weak_areas: list[str]       # 우선 대비 필요 영역 (MatchResult.weaknesses 요약)
    excluded_categories: list[str]  # 데이터 부족으로 제외된 카테고리 (비어있으면 전체 생성됨)


# ═══════════════════════════════════════════════════
# 전형 단계 (회사별 유동적 채용 프로세스)
# ═══════════════════════════════════════════════════


class ApplicationStage(BaseModel):
    """지원 건의 개별 전형 단계.

    회사마다 채용 프로세스가 다르므로 (코딩테스트, 과제, AI면접 등)
    stage_name을 자유 입력으로 두어 유연하게 대응.
    """

    stage_name: str  # "서류전형", "코딩테스트", "과제전형", "1차면접", "AI면접" 등
    stage_order: int
    status: StageStatus = StageStatus.PENDING
    scheduled_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    notes: Optional[str] = None


# ═══════════════════════════════════════════════════
# Gmail Monitor
# ═══════════════════════════════════════════════════


class InterviewDetails(BaseModel):
    """면접 상세 정보 (면접 안내 메일에서 추출)."""

    datetime_str: Optional[str] = None  # ISO8601
    location: Optional[str] = None
    format: Optional[str] = None  # "online" | "offline"
    platform: Optional[str] = None  # "Zoom", "Google Meet" 등
    duration_minutes: Optional[int] = None


class GmailParseResult(BaseModel):
    """Gmail Monitor LLM 파싱 출력.

    수신된 메일을 분석하여 채용 상태 변화를 구조화.
    """

    company: str
    status_type: GmailStatusType
    stage_name: Optional[str] = None  # "코딩테스트", "1차면접" 등
    next_step: Optional[str] = None
    interview_details: Optional[InterviewDetails] = None
    raw_summary: str = ""


# ═══════════════════════════════════════════════════
# Status Update
# ═══════════════════════════════════════════════════


class StatusEvidence(BaseModel):
    """상태 변경 근거."""

    gmail_event_id: Optional[str] = None
    summary: Optional[str] = None


class StatusUpdateRequest(BaseModel):
    """상태 변경 요청.

    모든 파이프라인에서 applications.status를 갱신할 때 사용하는 공통 인터페이스.
    status_history 테이블에 이력이 자동 기록됨.
    """

    application_id: str  # UUID
    new_status: ApplicationStatus
    trigger_type: TriggerType
    triggered_by: str  # "user" | "gmail_monitor" | "apply_pipeline" | "agent"
    evidence: Optional[StatusEvidence] = None
    note: Optional[str] = None


class StatusUpdateResponse(BaseModel):
    """상태 변경 응답."""

    success: bool
    application_id: str
    previous_status: ApplicationStatus
    new_status: ApplicationStatus
    history_id: Optional[str] = None  # status_history row ID
    updated_at: Optional[str] = None


# ═══════════════════════════════════════════════════
# Apply Pipeline
# ═══════════════════════════════════════════════════


class CalendarEventResult(BaseModel):
    """Calendar 이벤트 생성 결과."""

    event_type: str  # "deadline" | "interview" | "follow_up"
    google_event_id: Optional[str] = None
    title: str
    start_datetime: str
    sync_status: str = "pending"  # "pending" | "synced" | "failed"


class ApplyRequest(BaseModel):
    """지원 액션 요청.

    사용자가 지원을 승인하면 Apply Pipeline이 실행:
    DB 저장 → Calendar 등록 → 상태 업데이트.
    """

    user_id: str  # UUID
    job_posting_id: str  # UUID
    resume_id: str  # UUID
    company_name: str
    position: str
    ats_score: Optional[float] = None
    gap_summary: Optional[str] = None
    matched_keywords: list[str] = Field(default_factory=list)
    missing_keywords: list[str] = Field(default_factory=list)
    deadline: Optional[str] = None  # YYYY-MM-DD
    optimized_resume_url: Optional[str] = None
    cover_letter: Optional[str] = None


class ApplyResponse(BaseModel):
    """지원 액션 응답."""

    success: bool
    application_id: Optional[str] = None
    calendar_events: list[CalendarEventResult] = Field(default_factory=list)
    created_at: Optional[str] = None
