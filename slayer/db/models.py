"""Supabase PostgreSQL DB models.

10개 테이블:
    1. users              — 사용자 계정 + Google OAuth
    2. resumes            — 이력서 원본 + OCR 파싱 결과
    3. companies          — 기업 리서치 정보
    4. job_postings       — JD 파싱 결과
    5. applications       — 지원 현황 (핵심 테이블)
    6. application_stages — 회사별 전형 단계 (유동적)
    7. status_history     — 상태 변경 이력
    8. gmail_events       — Gmail 이메일 이벤트
    9. calendar_events    — Google Calendar 일정
   10. agent_logs         — Agent/Pipeline 실행 로그
"""

from sqlalchemy import (
    CheckConstraint, Column, String, Text, Boolean, Integer, Float,
    Date, DateTime, ForeignKey, Index, func,
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import DeclarativeBase, relationship
import uuid


class Base(DeclarativeBase):
    pass


# ═══════════════════════════════════════════════════
# 1. Users
# ═══════════════════════════════════════════════════


class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    google_id = Column(String(255), unique=True, nullable=False)
    email = Column(String(255), unique=True, nullable=False)
    name = Column(String(100), nullable=False)
    picture_url = Column(Text)
    google_access_token = Column(Text)
    google_refresh_token = Column(Text)
    token_expires_at = Column(DateTime(timezone=True))
    supabase_refresh_token = Column(Text)
    gmail_last_history_id = Column(String(50))
    gmail_last_poll_at = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    resumes = relationship("Resume", back_populates="user")
    applications = relationship("Application", back_populates="user")
    status_history = relationship("StatusHistory", back_populates="user")
    gmail_events = relationship("GmailEvent", back_populates="user")
    calendar_events = relationship("CalendarEvent", back_populates="user")
    agent_logs = relationship("AgentLog", back_populates="user")


# ═══════════════════════════════════════════════════
# 2. Resumes
# ═══════════════════════════════════════════════════


class Resume(Base):
    __tablename__ = "resumes"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    file_name = Column(String(255), nullable=False)
    file_type = Column(String(10), nullable=False)          # pdf | docx
    source_format = Column(String(10))                      # pdf | docx | md | json | txt
    file_url = Column(Text, nullable=False)
    parse_status = Column(String(20), nullable=False, default="pending")
    parsed_data = Column(JSONB)                             # ParsedResume 전체
    parse_error = Column(Text)
    is_primary = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    user = relationship("User", back_populates="resumes")
    applications = relationship("Application", back_populates="resume")


# ═══════════════════════════════════════════════════
# 3. Companies
# ═══════════════════════════════════════════════════


class Company(Base):
    """CompanyResearchOutput 스키마 기반."""
    __tablename__ = "companies"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), unique=True, nullable=False)
    name_en = Column(String(255))
    crno = Column(String(20), unique=True)                  # 법인등록번호
    industry = Column(String(100))
    ceo = Column(String(100))
    founded_date = Column(String(20))                       # API "19690113" 형식
    employee_count = Column(String(50))                     # API "28,394" 형식
    headquarters = Column(String(255))
    summary = Column(Text)
    basic_info = Column(JSONB)                              # BasicInfo
    financial_info = Column(JSONB)                          # FinancialInfo
    recent_news = Column(JSONB)                             # list[NewsItem]
    data_sources = Column(JSONB)                            # list[str]
    researched_at = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    job_postings = relationship("JobPosting", back_populates="company")
    applications = relationship("Application", back_populates="company")


# ═══════════════════════════════════════════════════
# 4. Job Postings
# ═══════════════════════════════════════════════════


class JobPosting(Base):
    """JDSchema 스키마 기반."""
    __tablename__ = "job_postings"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_id = Column(UUID(as_uuid=True), ForeignKey("companies.id"), index=True)
    source_url = Column(Text)
    platform = Column(String(50))                           # wanted | jobkorea | saramin | other
    title = Column(String(255))
    position = Column(String(255), nullable=False)
    location = Column(String(255))
    employment_type = Column(String(50))
    experience_level = Column(String(50))
    skills = Column(JSONB)                                  # 정규화된 스킬 리스트
    deadline = Column(Date)
    parsed_data = Column(JSONB)                             # JDSchema 전체
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        Index("ix_job_postings_skills", "skills", postgresql_using="gin"),
    )

    company = relationship("Company", back_populates="job_postings")
    applications = relationship("Application", back_populates="job_posting")


# ═══════════════════════════════════════════════════
# 5. Applications (핵심 테이블)
# ═══════════════════════════════════════════════════


class Application(Base):
    __tablename__ = "applications"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    company_id = Column(UUID(as_uuid=True), ForeignKey("companies.id"), nullable=False)
    job_posting_id = Column(UUID(as_uuid=True), ForeignKey("job_postings.id"), index=True)
    resume_id = Column(UUID(as_uuid=True), ForeignKey("resumes.id"), index=True)

    # 상위 상태 (ApplicationStatus enum — 7개)
    status = Column(String(30), nullable=False, default="scrapped")

    # 매칭 결과 (MatchResult 스키마)
    ats_score = Column(Float)
    score_breakdown = Column(JSONB)                         # 가중치별 점수
    matched_keywords = Column(JSONB)
    missing_keywords = Column(JSONB)
    strengths = Column(JSONB)
    weaknesses = Column(JSONB)
    gap_summary = Column(Text)

    # 최적화 (ResumeOptimizationOutput)
    optimized_resume_url = Column(Text)
    optimization_data = Column(JSONB)

    # 자소서 (CoverLetterOutput)
    cover_letter_text = Column(Text)
    cover_letter_metadata = Column(JSONB)                   # key_points, coverage, word_count

    interview_questions = Column(JSONB)
    applied_at = Column(DateTime(timezone=True))
    deadline = Column(Date)
    notes = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        Index("ix_applications_user_status", "user_id", "status"),
        CheckConstraint(
            "status IN ('scrapped','reviewing','applied','in_progress','final_pass','rejected','withdrawn')",
            name="ck_applications_status",
        ),
    )

    user = relationship("User", back_populates="applications")
    company = relationship("Company", back_populates="applications")
    job_posting = relationship("JobPosting", back_populates="applications")
    resume = relationship("Resume", back_populates="applications")
    stages = relationship("ApplicationStage", back_populates="application", order_by="ApplicationStage.stage_order")
    status_history = relationship("StatusHistory", back_populates="application")
    gmail_events = relationship("GmailEvent", back_populates="application")
    calendar_events = relationship("CalendarEvent", back_populates="application")
    agent_logs = relationship("AgentLog", back_populates="application")


# ═══════════════════════════════════════════════════
# 6. Application Stages (회사별 유동적 전형 단계)
# ═══════════════════════════════════════════════════


class ApplicationStage(Base):
    __tablename__ = "application_stages"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    application_id = Column(UUID(as_uuid=True), ForeignKey("applications.id"), nullable=False, index=True)
    stage_name = Column(String(100), nullable=False)        # "서류전형", "코딩테스트", "1차면접" 등
    stage_order = Column(Integer, nullable=False)
    status = Column(String(20), nullable=False, default="pending")  # pending | passed | failed
    scheduled_at = Column(DateTime(timezone=True))
    completed_at = Column(DateTime(timezone=True))
    notes = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        CheckConstraint(
            "status IN ('pending','passed','failed')",
            name="ck_application_stages_status",
        ),
    )

    application = relationship("Application", back_populates="stages")
    status_history = relationship("StatusHistory", back_populates="stage")
    calendar_events = relationship("CalendarEvent", back_populates="stage")


# ═══════════════════════════════════════════════════
# 7. Status History
# ═══════════════════════════════════════════════════


class StatusHistory(Base):
    __tablename__ = "status_history"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    application_id = Column(UUID(as_uuid=True), ForeignKey("applications.id"), nullable=False, index=True)
    stage_id = Column(UUID(as_uuid=True), ForeignKey("application_stages.id"), index=True)
    previous_status = Column(String(30), nullable=False)
    new_status = Column(String(30), nullable=False)
    trigger_type = Column(String(30), nullable=False)       # email_detected | user_manual | apply_action | agent_auto
    triggered_by = Column(String(30), nullable=False)       # user | gmail_monitor | apply_pipeline | agent
    evidence_gmail_event_id = Column(UUID(as_uuid=True), ForeignKey("gmail_events.id"))
    evidence_summary = Column(Text)
    note = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User", back_populates="status_history")
    application = relationship("Application", back_populates="status_history")
    stage = relationship("ApplicationStage", back_populates="status_history")
    evidence_gmail_event = relationship("GmailEvent")


# ═══════════════════════════════════════════════════
# 8. Gmail Events
# ═══════════════════════════════════════════════════


class GmailEvent(Base):
    __tablename__ = "gmail_events"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    application_id = Column(UUID(as_uuid=True), ForeignKey("applications.id"), index=True)
    gmail_message_id = Column(String(255), unique=True, nullable=False)
    subject = Column(Text)
    sender = Column(String(255))
    received_at = Column(DateTime(timezone=True), nullable=False)
    raw_snippet = Column(Text)
    parsed_company = Column(String(255))
    parsed_status_type = Column(String(20))                 # PASS | FAIL | INTERVIEW | REJECT
    parsed_stage_name = Column(String(100))                 # "코딩테스트", "1차면접" 등
    parsed_next_step = Column(Text)
    interview_datetime = Column(DateTime(timezone=True))
    interview_details = Column(JSONB)                       # InterviewDetails (location, format, platform, duration)
    raw_summary = Column(Text)
    process_status = Column(String(20), default="unprocessed")
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User", back_populates="gmail_events")
    application = relationship("Application", back_populates="gmail_events")


# ═══════════════════════════════════════════════════
# 9. Calendar Events
# ═══════════════════════════════════════════════════


class CalendarEvent(Base):
    __tablename__ = "calendar_events"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    application_id = Column(UUID(as_uuid=True), ForeignKey("applications.id"), index=True)
    stage_id = Column(UUID(as_uuid=True), ForeignKey("application_stages.id"), index=True)
    gmail_event_id = Column(UUID(as_uuid=True), ForeignKey("gmail_events.id"), index=True)
    google_event_id = Column(String(255), unique=True)
    event_type = Column(String(30), nullable=False)         # deadline | interview | follow_up
    title = Column(String(255), nullable=False)
    description = Column(Text)
    start_datetime = Column(DateTime(timezone=True), nullable=False)
    end_datetime = Column(DateTime(timezone=True))
    location = Column(Text)
    is_all_day = Column(Boolean, default=False)
    sync_status = Column(String(20), default="pending")     # pending | synced | failed
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User", back_populates="calendar_events")
    application = relationship("Application", back_populates="calendar_events")
    stage = relationship("ApplicationStage", back_populates="calendar_events")
    gmail_event = relationship("GmailEvent")


# ═══════════════════════════════════════════════════
# 10. Agent Logs
# ═══════════════════════════════════════════════════


class AgentLog(Base):
    __tablename__ = "agent_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), index=True)
    application_id = Column(UUID(as_uuid=True), ForeignKey("applications.id"), index=True)
    agent_name = Column(String(100), nullable=False)
    status = Column(String(20), nullable=False)             # success | failed | partial
    input_summary = Column(Text)
    output_summary = Column(Text)
    tokens_used = Column(Integer)
    duration_ms = Column(Integer)
    error_message = Column(Text)
    extra_metadata = Column(JSONB)                          # renamed from metadata (SQLAlchemy 예약어)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User", back_populates="agent_logs")
    application = relationship("Application", back_populates="agent_logs")
