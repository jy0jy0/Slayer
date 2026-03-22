"""GCP PostgreSQL DB models.

DRAFT - 팀 리뷰 후 확정
예신님 구글시트 스키마 기반 (Discussion #6)
https://docs.google.com/spreadsheets/d/1gOh79ZR4dnNeAnkbkJ_c9eLpTyC6LUNgi_crF4MtEUs

9개 테이블:
    1. users           — 사용자 계정 + Google OAuth
    2. resumes         — 이력서 원본 + OCR 파싱 결과
    3. companies       — 기업 리서치 정보
    4. job_postings    — JD 파싱 결과
    5. applications    — 지원 현황 (핵심 테이블)
    6. status_history  — 상태 변경 이력
    7. gmail_events    — Gmail 이메일 이벤트
    8. calendar_events — Google Calendar 일정
    9. agent_logs      — Agent/Pipeline 실행 로그
"""

# from sqlalchemy import (
#     Column, String, Text, Boolean, Integer, SmallInteger,
#     Date, DateTime, ForeignKey, JSON, func
# )
# from sqlalchemy.dialects.postgresql import UUID, JSONB
# from sqlalchemy.orm import DeclarativeBase, relationship
# import uuid
#
#
# class Base(DeclarativeBase):
#     pass
#
#
# class User(Base):
#     __tablename__ = "users"
#
#     id = Column(UUID, primary_key=True, default=uuid.uuid4)
#     google_id = Column(String(255), unique=True, nullable=False)
#     email = Column(String(255), unique=True, nullable=False)
#     name = Column(String(100), nullable=False)
#     picture_url = Column(Text)
#     google_access_token = Column(Text)       # 암호화 저장
#     google_refresh_token = Column(Text)      # 암호화 저장
#     token_expires_at = Column(DateTime(timezone=True))
#     gmail_last_history_id = Column(String(50))
#     gmail_last_poll_at = Column(DateTime(timezone=True))
#     created_at = Column(DateTime(timezone=True), server_default=func.now())
#     updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
#
#
# class Resume(Base):
#     __tablename__ = "resumes"
#
#     id = Column(UUID, primary_key=True, default=uuid.uuid4)
#     user_id = Column(UUID, ForeignKey("users.id"), nullable=False)
#     file_name = Column(String(255), nullable=False)
#     file_type = Column(String(10), nullable=False)     # pdf | docx
#     file_url = Column(Text, nullable=False)             # GCS / S3 URL
#     parse_status = Column(String(20), nullable=False, default="pending")  # pending|processing|success|failed
#     parsed_data = Column(JSONB)                         # OCR Pipeline 출력 전체
#     parse_error = Column(Text)
#     is_primary = Column(Boolean, default=False)
#     created_at = Column(DateTime(timezone=True), server_default=func.now())
#     updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
#
#
# class Company(Base):
#     __tablename__ = "companies"
#
#     id = Column(UUID, primary_key=True, default=uuid.uuid4)
#     name = Column(String(255), unique=True, nullable=False)
#     crno = Column(String(20), unique=True)              # 법인등록번호
#     industry = Column(String(100))
#     employee_count = Column(Integer)
#     founded_year = Column(Integer)
#     website_url = Column(Text)
#     research_report = Column(JSONB)                     # Research Agent 출력
#     news_snapshot = Column(JSONB)
#     financial_snapshot = Column(JSONB)
#     researched_at = Column(DateTime(timezone=True))
#     created_at = Column(DateTime(timezone=True), server_default=func.now())
#
#
# class JobPosting(Base):
#     __tablename__ = "job_postings"
#
#     id = Column(UUID, primary_key=True, default=uuid.uuid4)
#     company_id = Column(UUID, ForeignKey("companies.id"))
#     source_url = Column(Text)
#     source_platform = Column(String(50))                # wanted|jobkorea|saramin|other
#     position = Column(String(255), nullable=False)
#     required_skills = Column(JSONB)
#     preferred_skills = Column(JSONB)
#     qualifications = Column(Text)
#     responsibilities = Column(Text)
#     deadline = Column(Date)
#     parsed_data = Column(JSONB)                         # JD Pipeline 출력
#     created_at = Column(DateTime(timezone=True), server_default=func.now())
#
#
# class Application(Base):
#     """핵심 테이블 — 모든 파이프라인이 읽고 씀."""
#     __tablename__ = "applications"
#
#     id = Column(UUID, primary_key=True, default=uuid.uuid4)
#     user_id = Column(UUID, ForeignKey("users.id"), nullable=False)
#     company_id = Column(UUID, ForeignKey("companies.id"), nullable=False)
#     job_posting_id = Column(UUID, ForeignKey("job_postings.id"))
#     resume_id = Column(UUID, ForeignKey("resumes.id"))
#     status = Column(String(30), nullable=False, default="scrapped")
#     # scrapped|reviewing|applied|document_pass|interview_1|interview_2|interview_3|final_pass|rejected|withdrawn
#     ats_score = Column(SmallInteger)                    # 0~100
#     gap_summary = Column(Text)
#     matching_keywords = Column(JSONB)
#     missing_keywords = Column(JSONB)
#     optimized_resume_url = Column(Text)
#     cover_letter = Column(Text)
#     interview_questions = Column(JSONB)
#     applied_at = Column(DateTime(timezone=True))
#     deadline = Column(Date)
#     notes = Column(Text)
#     created_at = Column(DateTime(timezone=True), server_default=func.now())
#     updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
#
#
# class StatusHistory(Base):
#     __tablename__ = "status_history"
#
#     id = Column(UUID, primary_key=True, default=uuid.uuid4)
#     user_id = Column(UUID, ForeignKey("users.id"), nullable=False)
#     application_id = Column(UUID, ForeignKey("applications.id"), nullable=False)
#     previous_status = Column(String(30), nullable=False)
#     new_status = Column(String(30), nullable=False)
#     trigger_type = Column(String(30), nullable=False)   # email_detected|user_manual|apply_action|agent_auto
#     triggered_by = Column(String(30), nullable=False)    # user|gmail_monitor|apply_pipeline|agent
#     evidence_gmail_event_id = Column(UUID, ForeignKey("gmail_events.id"))
#     evidence_summary = Column(Text)
#     note = Column(Text)
#     created_at = Column(DateTime(timezone=True), server_default=func.now())
#
#
# class GmailEvent(Base):
#     __tablename__ = "gmail_events"
#
#     id = Column(UUID, primary_key=True, default=uuid.uuid4)
#     user_id = Column(UUID, ForeignKey("users.id"), nullable=False)
#     application_id = Column(UUID, ForeignKey("applications.id"))
#     gmail_message_id = Column(String(255), unique=True, nullable=False)
#     subject = Column(Text)
#     sender = Column(String(255))
#     received_at = Column(DateTime(timezone=True), nullable=False)
#     raw_snippet = Column(Text)
#     parsed_company = Column(String(255))
#     parsed_status_type = Column(String(20))             # PASS|FAIL|INTERVIEW|REJECT
#     parsed_next_step = Column(Text)
#     interview_datetime = Column(DateTime(timezone=True))
#     interview_location = Column(Text)
#     interview_format = Column(String(20))               # online|offline
#     raw_summary = Column(Text)
#     process_status = Column(String(20), default="unprocessed")  # unprocessed|processed|error
#     created_at = Column(DateTime(timezone=True), server_default=func.now())
#
#
# class CalendarEvent(Base):
#     __tablename__ = "calendar_events"
#
#     id = Column(UUID, primary_key=True, default=uuid.uuid4)
#     user_id = Column(UUID, ForeignKey("users.id"), nullable=False)
#     application_id = Column(UUID, ForeignKey("applications.id"))
#     gmail_event_id = Column(UUID, ForeignKey("gmail_events.id"))
#     google_event_id = Column(String(255), unique=True)
#     event_type = Column(String(30), nullable=False)     # deadline|interview|follow_up
#     title = Column(String(255), nullable=False)
#     description = Column(Text)
#     start_datetime = Column(DateTime(timezone=True), nullable=False)
#     end_datetime = Column(DateTime(timezone=True))
#     location = Column(Text)
#     is_all_day = Column(Boolean, default=False)
#     sync_status = Column(String(20), default="pending")  # pending|synced|failed
#     created_at = Column(DateTime(timezone=True), server_default=func.now())
#
#
# class AgentLog(Base):
#     __tablename__ = "agent_logs"
#
#     id = Column(UUID, primary_key=True, default=uuid.uuid4)
#     user_id = Column(UUID, ForeignKey("users.id"))
#     application_id = Column(UUID, ForeignKey("applications.id"))
#     agent_name = Column(String(100), nullable=False)    # ocr_pipeline|gmail_monitor|apply_pipeline|match_pipeline|...
#     status = Column(String(20), nullable=False)          # success|failed|partial
#     input_summary = Column(Text)
#     output_summary = Column(Text)
#     tokens_used = Column(Integer)
#     duration_ms = Column(Integer)
#     error_message = Column(Text)
#     metadata = Column(JSONB)
#     created_at = Column(DateTime(timezone=True), server_default=func.now())
