"""공용 테스트 픽스처."""

import pytest

from slayer.schemas import (
    BasicInfo,
    CompanyResearchOutput,
    CoverLetterInput,
    EducationItem,
    ExperienceItem,
    FinancialInfo,
    JDOverview,
    JDRequirements,
    JDSchema,
    MatchResult,
    NewsItem,
    ParsedResume,
    PersonalInfo,
    ProjectItem,
    ResumeOptimizationInput,
)


@pytest.fixture
def sample_jd() -> JDSchema:
    return JDSchema(
        company="카카오",
        title="백엔드 엔지니어",
        position="서버 개발",
        overview=JDOverview(
            employment_type="정규직",
            experience="경력 3년 이상",
            location="경기도 성남시",
        ),
        responsibilities=["백엔드 시스템 설계", "API 개발", "DB 최적화"],
        requirements=JDRequirements(
            required=["Python 3년 이상", "RESTful API", "RDBMS"],
            preferred=["Kubernetes", "AWS", "Kafka"],
        ),
        skills=["python", "fastapi", "postgresql", "kubernetes", "docker", "aws"],
        process=["서류", "코딩테스트", "면접"],
        platform="wanted",
    )


@pytest.fixture
def sample_resume() -> ParsedResume:
    return ParsedResume(
        personal_info=PersonalInfo(
            name="김개발",
            email="dev@test.com",
            phone="010-1234-5678",
        ),
        summary="Python 백엔드 3년차 개발자",
        experiences=[
            ExperienceItem(
                company="스타트업A",
                position="백엔드 개발자",
                start_date="2023-03",
                is_current=True,
                description="FastAPI 기반 API 서버 개발",
                achievements=["일 50만 요청 처리", "응답시간 40% 개선"],
            ),
        ],
        projects=[
            ProjectItem(
                name="실시간 알림 시스템",
                role="리드",
                description="WebSocket 기반",
                tech_stack=["python", "fastapi", "redis"],
            ),
        ],
        education=[
            EducationItem(
                school="서울대학교",
                major="컴퓨터공학",
                degree="학사",
            ),
        ],
        skills=["python", "fastapi", "django", "postgresql", "redis", "docker", "git"],
        total_years_experience=3.0,
    )


@pytest.fixture
def sample_match_result() -> MatchResult:
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
        missing_keywords=["kubernetes", "aws", "kafka", "ci/cd"],
        strengths=["Python 백엔드 경험", "FastAPI 프로젝트"],
        weaknesses=["클라우드 경험 부족", "DevOps 키워드 누락"],
        gap_summary="백엔드 핵심 역량은 있으나 클라우드/인프라 경험 부족",
    )


@pytest.fixture
def sample_company_research() -> CompanyResearchOutput:
    return CompanyResearchOutput(
        company_name="카카오",
        company_name_en="Kakao Corp",
        basic_info=BasicInfo(
            industry="IT/소프트웨어",
            ceo="홍은택",
            employee_count="7000",
            headquarters="경기도 성남시 분당구",
        ),
        financial_info=FinancialInfo(
            revenue="7조 1천억",
            operating_profit="3천억",
            fiscal_year="2025",
        ),
        recent_news=[
            NewsItem(title="카카오 AI 서비스 확대", summary="카카오가 AI 기반 서비스를 확대한다."),
        ],
        summary="국내 대표 IT 플랫폼 기업. 메신저, 커머스, 모빌리티 등 다양한 서비스 운영.",
        data_sources=["naver_news", "corp_info", "financial_info"],
        researched_at="2026-03-29T12:00:00",
    )
