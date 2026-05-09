"""Pipeline API 엔드포인트 테스트.

테스트 대상:
    POST /api/v1/pipelines/company-research  — 기업 리서치
    POST /api/v1/pipelines/jd/parse          — JD URL 파싱
    POST /api/v1/pipelines/match             — JD↔이력서 매칭
    POST /api/v1/pipelines/optimize          — 이력서 최적화
    POST /api/v1/pipelines/cover-letter      — 자소서 생성
    POST /api/v1/pipelines/interview         — 면접 질문 생성

모든 외부 의존성(LLM, 크롤러, DB)은 unittest.mock으로 차단하여
CI 환경에서도 통과하도록 설계.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from slayer.api.main import create_app


# ──────────────────────────────────────────────────────────────
# 픽스처
# ──────────────────────────────────────────────────────────────


@pytest.fixture
def client() -> TestClient:
    app = create_app()
    return TestClient(app)


# ──────────────────────────────────────────────────────────────
# 샘플 요청 데이터
# ──────────────────────────────────────────────────────────────


def _jd_dict() -> dict:
    return {
        "company": "카카오",
        "title": "백엔드 엔지니어",
        "position": "서버 개발",
        "overview": {
            "employment_type": "정규직",
            "experience": "3년 이상",
            "location": "경기도 성남시",
        },
        "responsibilities": ["백엔드 API 개발", "DB 설계"],
        "requirements": {
            "required": ["Python 3년", "FastAPI", "PostgreSQL"],
            "preferred": ["Kubernetes", "AWS"],
        },
        "skills": ["python", "fastapi", "postgresql", "docker"],
        "process": ["서류", "코딩테스트", "면접"],
        "platform": "wanted",
    }


def _resume_dict() -> dict:
    return {
        "personal_info": {
            "name": "김개발",
            "email": "dev@test.com",
            "phone": "010-1234-5678",
        },
        "summary": "Python 백엔드 3년차 개발자",
        "experiences": [
            {
                "company": "스타트업A",
                "position": "백엔드 개발자",
                "start_date": "2023-03",
                "is_current": True,
                "description": "FastAPI 기반 API 서버 개발",
                "achievements": ["일 50만 요청 처리"],
            }
        ],
        "projects": [],
        "education": [
            {"school": "서울대학교", "major": "컴퓨터공학", "degree": "학사"}
        ],
        "skills": ["python", "fastapi", "docker", "postgresql"],
        "total_years_experience": 3.0,
    }


def _match_result_dict() -> dict:
    return {
        "ats_score": 72.0,
        "score_breakdown": {"ats_simulation": 20.0, "keywords": 15.0},
        "matched_keywords": ["python", "fastapi", "docker"],
        "missing_keywords": ["kubernetes", "aws"],
        "strengths": ["Python 백엔드 경험", "FastAPI 프로젝트"],
        "weaknesses": ["클라우드 경험 부족"],
        "gap_summary": "핵심 역량은 있으나 인프라/클라우드 경험 부족",
    }


def _company_research_dict() -> dict:
    return {
        "company_name": "카카오",
        "company_name_en": "Kakao Corp",
        "summary": "국내 대표 IT 플랫폼 기업",
        "data_sources": ["naver_news", "corp_info"],
        "researched_at": "2026-04-11T00:00:00",
    }


# ──────────────────────────────────────────────────────────────
# POST /api/v1/pipelines/company-research
# ──────────────────────────────────────────────────────────────


class TestCompanyResearch:
    """기업 리서치 엔드포인트 테스트."""

    def test_success(self, client: TestClient):
        """정상 리서치 → 200, company_name 포함."""
        from slayer.schemas import CompanyResearchOutput

        mock_output = CompanyResearchOutput(
            company_name="카카오",
            company_name_en="Kakao Corp",
            summary="국내 대표 IT 기업",
            data_sources=["naver_news"],
            researched_at="2026-04-11T00:00:00",
        )
        with patch(
            "slayer.agents.company_research.agent.run_company_research_streaming",
            new=AsyncMock(return_value=mock_output),
        ):
            response = client.post(
                "/api/v1/pipelines/company-research",
                json={"company_name": "카카오"},
            )

        assert response.status_code == 200
        body = response.json()
        assert body["company_name"] == "카카오"
        assert body["company_name_en"] == "Kakao Corp"
        assert "summary" in body
        assert "data_sources" in body

    def test_empty_company_name(self, client: TestClient):
        """빈 company_name → 400."""
        response = client.post(
            "/api/v1/pipelines/company-research",
            json={"company_name": "   "},
        )
        assert response.status_code == 400
        assert "company_name" in response.json()["detail"]

    def test_missing_company_name_field(self, client: TestClient):
        """company_name 필드 누락 → 422 (Pydantic validation)."""
        response = client.post("/api/v1/pipelines/company-research", json={})
        assert response.status_code == 422

    def test_agent_failure(self, client: TestClient):
        """에이전트 런타임 오류 → 500."""
        with patch(
            "slayer.agents.company_research.agent.run_company_research_streaming",
            new=AsyncMock(side_effect=RuntimeError("외부 API 오류")),
        ):
            response = client.post(
                "/api/v1/pipelines/company-research",
                json={"company_name": "카카오"},
            )
        assert response.status_code == 500

    def test_response_includes_researched_at(self, client: TestClient):
        """응답에 researched_at 타임스탬프 포함 확인."""
        from slayer.schemas import CompanyResearchOutput

        mock_output = CompanyResearchOutput(
            company_name="네이버",
            summary="국내 검색 포털",
            data_sources=[],
            researched_at="2026-04-11T12:00:00",
        )
        with patch(
            "slayer.agents.company_research.agent.run_company_research_streaming",
            new=AsyncMock(return_value=mock_output),
        ):
            response = client.post(
                "/api/v1/pipelines/company-research",
                json={"company_name": "네이버"},
            )

        assert response.status_code == 200
        assert response.json()["researched_at"] == "2026-04-11T12:00:00"


# ──────────────────────────────────────────────────────────────
# POST /api/v1/pipelines/jd/parse
# ──────────────────────────────────────────────────────────────


class TestJDParse:
    """JD 파싱 엔드포인트 테스트."""

    def test_success(self, client: TestClient):
        """정상 URL → 200, JD 구조 반환."""
        from slayer.schemas import JDRequirements, JDSchema

        mock_jd = JDSchema(
            company="카카오",
            title="백엔드 엔지니어",
            position="서버 개발",
            responsibilities=["API 개발"],
            requirements=JDRequirements(
                required=["Python", "FastAPI"],
                preferred=["Kubernetes"],
            ),
            skills=["python", "fastapi"],
            process=["서류", "면접"],
            platform="wanted",
        )
        with patch(
            "slayer.pipelines.jd_parser.scraper.scrape_jd",
            new=AsyncMock(return_value=mock_jd),
        ):
            response = client.post(
                "/api/v1/pipelines/jd/parse",
                json={"url": "https://www.wanted.co.kr/wd/12345"},
            )

        assert response.status_code == 200
        body = response.json()
        assert body["company"] == "카카오"
        assert body["title"] == "백엔드 엔지니어"
        assert "skills" in body
        assert "python" in body["skills"]

    def test_empty_url(self, client: TestClient):
        """빈 URL → 400."""
        response = client.post("/api/v1/pipelines/jd/parse", json={"url": ""})
        assert response.status_code == 400
        assert "url" in response.json()["detail"]

    def test_missing_url_field(self, client: TestClient):
        """url 필드 누락 → 422."""
        response = client.post("/api/v1/pipelines/jd/parse", json={})
        assert response.status_code == 422

    def test_scraper_failure(self, client: TestClient):
        """크롤링 실패 → 500."""
        with patch(
            "slayer.pipelines.jd_parser.scraper.scrape_jd",
            new=AsyncMock(side_effect=RuntimeError("크롤링 타임아웃")),
        ):
            response = client.post(
                "/api/v1/pipelines/jd/parse",
                json={"url": "https://www.wanted.co.kr/wd/99999"},
            )
        assert response.status_code == 500

    def test_response_has_requirements(self, client: TestClient):
        """응답에 requirements.required 포함 확인."""
        from slayer.schemas import JDRequirements, JDSchema

        mock_jd = JDSchema(
            company="라인",
            title="프론트엔드 개발자",
            position="프론트엔드 개발",
            responsibilities=[],
            requirements=JDRequirements(
                required=["React", "TypeScript"],
                preferred=[],
            ),
            skills=["react", "typescript"],
            process=[],
            platform="jobplanet",
        )
        with patch(
            "slayer.pipelines.jd_parser.scraper.scrape_jd",
            new=AsyncMock(return_value=mock_jd),
        ):
            response = client.post(
                "/api/v1/pipelines/jd/parse",
                json={"url": "https://jobplanet.co.kr/jobs/1"},
            )

        assert response.status_code == 200
        body = response.json()
        assert "requirements" in body
        assert "React" in body["requirements"]["required"]


# ──────────────────────────────────────────────────────────────
# POST /api/v1/pipelines/match
# ──────────────────────────────────────────────────────────────


class TestMatch:
    """JD↔이력서 매칭 엔드포인트 테스트."""

    def test_success(self, client: TestClient):
        """정상 JD + 이력서 → 200, ATS 점수 포함."""
        from slayer.schemas import MatchResult

        mock_result = MatchResult(
            ats_score=72.0,
            score_breakdown={"ats_simulation": 20.0, "keywords": 15.0},
            matched_keywords=["python", "fastapi", "docker"],
            missing_keywords=["kubernetes", "aws"],
            strengths=["Python 백엔드 경험"],
            weaknesses=["클라우드 경험 부족"],
            gap_summary="핵심 역량은 있으나 인프라 경험 부족",
        )
        with patch(
            "slayer.pipelines.jd_resume_matcher.match_jd_resume",
            new=AsyncMock(return_value=mock_result),
        ):
            response = client.post(
                "/api/v1/pipelines/match",
                json={"jd": _jd_dict(), "resume": _resume_dict()},
            )

        assert response.status_code == 200
        body = response.json()
        assert body["ats_score"] == 72.0
        assert "matched_keywords" in body
        assert "missing_keywords" in body
        assert "strengths" in body
        assert "weaknesses" in body

    def test_score_structure(self, client: TestClient):
        """score_breakdown 포함 확인."""
        from slayer.schemas import MatchResult

        mock_result = MatchResult(
            ats_score=55.0,
            score_breakdown={"ats_simulation": 15.0},
            matched_keywords=["python"],
            missing_keywords=["kubernetes", "aws", "kafka"],
            strengths=["Python 사용"],
            weaknesses=["클라우드 없음", "DevOps 없음"],
        )
        with patch(
            "slayer.pipelines.jd_resume_matcher.match_jd_resume",
            new=AsyncMock(return_value=mock_result),
        ):
            response = client.post(
                "/api/v1/pipelines/match",
                json={"jd": _jd_dict(), "resume": _resume_dict()},
            )

        assert response.status_code == 200
        body = response.json()
        assert "score_breakdown" in body
        assert len(body["missing_keywords"]) == 3

    def test_invalid_jd_schema(self, client: TestClient):
        """유효하지 않은 JD 구조 → 500 (ValidationError catch)."""
        response = client.post(
            "/api/v1/pipelines/match",
            json={"jd": {"invalid_key": True}, "resume": _resume_dict()},
        )
        assert response.status_code == 500

    def test_missing_body_fields(self, client: TestClient):
        """jd/resume 모두 누락 → 422."""
        response = client.post("/api/v1/pipelines/match", json={})
        assert response.status_code == 422

    def test_missing_resume(self, client: TestClient):
        """resume 누락 → 422."""
        response = client.post(
            "/api/v1/pipelines/match",
            json={"jd": _jd_dict()},
        )
        assert response.status_code == 422

    def test_matcher_failure(self, client: TestClient):
        """매처 런타임 오류 → 500."""
        with patch(
            "slayer.pipelines.jd_resume_matcher.match_jd_resume",
            new=AsyncMock(side_effect=RuntimeError("LLM 오류")),
        ):
            response = client.post(
                "/api/v1/pipelines/match",
                json={"jd": _jd_dict(), "resume": _resume_dict()},
            )
        assert response.status_code == 500


# ──────────────────────────────────────────────────────────────
# POST /api/v1/pipelines/optimize
# ──────────────────────────────────────────────────────────────


class TestOptimize:
    """이력서 최적화 엔드포인트 테스트."""

    def test_success(self, client: TestClient):
        """정상 입력 → 200, final_ats_score 포함."""
        from slayer.schemas import ResumeOptimizationOutput

        mock_result = ResumeOptimizationOutput(
            optimized_blocks=[],
            final_ats_score=85.0,
            score_improvement=13.0,
            changes=[],
            iterations_used=2,
            optimization_summary="누락 키워드 3개 보완 완료",
        )
        with patch(
            "slayer.agents.resume_optimizer.agent.optimize_resume_streaming",
            new=AsyncMock(return_value=mock_result),
        ):
            response = client.post(
                "/api/v1/pipelines/optimize",
                json={
                    "parsed_resume": _resume_dict(),
                    "jd": _jd_dict(),
                    "match_result": _match_result_dict(),
                },
            )

        assert response.status_code == 200
        body = response.json()
        assert body["final_ats_score"] == 85.0
        assert body["score_improvement"] == 13.0
        assert body["iterations_used"] == 2
        assert "optimization_summary" in body
        assert "optimized_blocks" in body

    def test_custom_target_score(self, client: TestClient):
        """target_ats_score 커스텀 값 전달 확인."""
        from slayer.schemas import ResumeOptimizationOutput

        mock_result = ResumeOptimizationOutput(
            optimized_blocks=[],
            final_ats_score=90.0,
            score_improvement=18.0,
            changes=[],
            iterations_used=3,
        )
        with patch(
            "slayer.agents.resume_optimizer.agent.optimize_resume_streaming",
            new=AsyncMock(return_value=mock_result),
        ) as mock_fn:
            response = client.post(
                "/api/v1/pipelines/optimize",
                json={
                    "parsed_resume": _resume_dict(),
                    "jd": _jd_dict(),
                    "match_result": _match_result_dict(),
                    "target_ats_score": 90.0,
                    "max_iterations": 5,
                },
            )

        assert response.status_code == 200
        assert mock_fn.called

    def test_missing_match_result(self, client: TestClient):
        """match_result 누락 → 422."""
        response = client.post(
            "/api/v1/pipelines/optimize",
            json={"parsed_resume": _resume_dict(), "jd": _jd_dict()},
        )
        assert response.status_code == 422

    def test_optimizer_failure(self, client: TestClient):
        """최적화 에이전트 오류 → 500."""
        with patch(
            "slayer.agents.resume_optimizer.agent.optimize_resume_streaming",
            new=AsyncMock(side_effect=RuntimeError("토큰 한도 초과")),
        ):
            response = client.post(
                "/api/v1/pipelines/optimize",
                json={
                    "parsed_resume": _resume_dict(),
                    "jd": _jd_dict(),
                    "match_result": _match_result_dict(),
                },
            )
        assert response.status_code == 500


# ──────────────────────────────────────────────────────────────
# POST /api/v1/pipelines/cover-letter
# ──────────────────────────────────────────────────────────────


class TestCoverLetter:
    """자소서 생성 엔드포인트 테스트."""

    def test_success_with_all_context(self, client: TestClient):
        """모든 컨텍스트 제공 → 200, cover_letter 포함."""
        from slayer.schemas import CoverLetterOutput

        mock_result = CoverLetterOutput(
            cover_letter="안녕하세요. 카카오 백엔드 엔지니어에 지원합니다...",
            key_points=["Python 3년 경험", "FastAPI 프로젝트 다수"],
            jd_keyword_coverage=0.75,
            word_count=500,
        )
        with patch(
            "slayer.agents.cover_letter.agent.generate_cover_letter_streaming",
            new=AsyncMock(return_value=mock_result),
        ):
            response = client.post(
                "/api/v1/pipelines/cover-letter",
                json={
                    "parsed_resume": _resume_dict(),
                    "jd": _jd_dict(),
                    "company_research": _company_research_dict(),
                    "match_result": _match_result_dict(),
                },
            )

        assert response.status_code == 200
        body = response.json()
        assert "cover_letter" in body
        assert body["word_count"] == 500
        assert body["jd_keyword_coverage"] == 0.75
        assert len(body["key_points"]) == 2

    def test_missing_jd(self, client: TestClient):
        """jd 누락 → 422."""
        response = client.post(
            "/api/v1/pipelines/cover-letter",
            json={"parsed_resume": _resume_dict()},
        )
        assert response.status_code == 422

    def test_missing_resume(self, client: TestClient):
        """parsed_resume 누락 → 422."""
        response = client.post(
            "/api/v1/pipelines/cover-letter",
            json={"jd": _jd_dict()},
        )
        assert response.status_code == 422

    def test_agent_failure(self, client: TestClient):
        """자소서 생성 에이전트 오류 → 500."""
        with patch(
            "slayer.agents.cover_letter.agent.generate_cover_letter_streaming",
            new=AsyncMock(side_effect=RuntimeError("API 오류")),
        ):
            response = client.post(
                "/api/v1/pipelines/cover-letter",
                json={
                    "parsed_resume": _resume_dict(),
                    "jd": _jd_dict(),
                    "company_research": _company_research_dict(),
                    "match_result": _match_result_dict(),
                },
            )
        assert response.status_code == 500


# ──────────────────────────────────────────────────────────────
# POST /api/v1/pipelines/interview
# ──────────────────────────────────────────────────────────────


class TestInterview:
    """면접 질문 생성 엔드포인트 테스트."""

    def test_success(self, client: TestClient):
        """정상 입력 → 200, questions 포함."""
        from slayer.schemas import (
            InterviewCategory,
            InterviewQuestion,
            InterviewQuestionsOutput,
        )

        mock_result = InterviewQuestionsOutput(
            questions=[
                InterviewQuestion(
                    category=InterviewCategory.TECHNICAL,
                    question="Python 비동기 처리를 설명해 주세요.",
                    intent="기술 깊이 확인",
                    tip="asyncio와 실제 사용 경험을 함께 설명하세요.",
                    source="skill: python",
                ),
                InterviewQuestion(
                    category=InterviewCategory.EXPERIENCE,
                    question="가장 어려웠던 기술적 문제를 어떻게 해결했나요?",
                    intent="문제 해결 능력 평가",
                    tip="STAR 기법으로 구체적 수치와 함께 설명하세요.",
                    source="experience: 스타트업A",
                ),
            ],
            sample_answers=[],
            weak_areas=["Kubernetes 경험 부족", "클라우드 인프라"],
            excluded_categories=[],
        )
        with patch(
            "slayer.pipelines.interview_questions.generate_interview_questions",
            return_value=mock_result,
        ):
            response = client.post(
                "/api/v1/pipelines/interview",
                json={
                    "jd": _jd_dict(),
                    "resume": _resume_dict(),
                    "questions_per_category": 2,
                },
            )

        assert response.status_code == 200
        body = response.json()
        assert "questions" in body
        assert len(body["questions"]) == 2
        assert body["questions"][0]["category"] == "기술"
        assert "weak_areas" in body
        assert len(body["weak_areas"]) == 2

    def test_with_all_optional_context(self, client: TestClient):
        """company_research + match_result 포함 → 200."""
        from slayer.schemas import InterviewQuestionsOutput

        mock_result = InterviewQuestionsOutput(
            questions=[],
            sample_answers=[],
            weak_areas=[],
            excluded_categories=[],
        )
        with patch(
            "slayer.pipelines.interview_questions.generate_interview_questions",
            return_value=mock_result,
        ):
            response = client.post(
                "/api/v1/pipelines/interview",
                json={
                    "jd": _jd_dict(),
                    "resume": _resume_dict(),
                    "company_research": _company_research_dict(),
                    "match_result": _match_result_dict(),
                },
            )

        assert response.status_code == 200

    def test_excluded_categories_returned(self, client: TestClient):
        """excluded_categories 필드 포함 확인."""
        from slayer.schemas import InterviewQuestionsOutput

        mock_result = InterviewQuestionsOutput(
            questions=[],
            sample_answers=[],
            weak_areas=[],
            excluded_categories=["컬처핏", "기업 이해도"],
        )
        with patch(
            "slayer.pipelines.interview_questions.generate_interview_questions",
            return_value=mock_result,
        ):
            response = client.post(
                "/api/v1/pipelines/interview",
                json={"jd": _jd_dict(), "resume": _resume_dict()},
            )

        assert response.status_code == 200
        body = response.json()
        assert "컬처핏" in body["excluded_categories"]

    def test_missing_jd(self, client: TestClient):
        """jd 누락 → 422."""
        response = client.post(
            "/api/v1/pipelines/interview",
            json={"resume": _resume_dict()},
        )
        assert response.status_code == 422

    def test_missing_resume(self, client: TestClient):
        """resume 누락 → 422."""
        response = client.post(
            "/api/v1/pipelines/interview",
            json={"jd": _jd_dict()},
        )
        assert response.status_code == 422

    def test_pipeline_failure(self, client: TestClient):
        """면접 질문 파이프라인 오류 → 500."""
        with patch(
            "slayer.pipelines.interview_questions.generate_interview_questions",
            side_effect=RuntimeError("LLM 오류"),
        ):
            response = client.post(
                "/api/v1/pipelines/interview",
                json={"jd": _jd_dict(), "resume": _resume_dict()},
            )
        assert response.status_code == 500

    def test_questions_per_category_default(self, client: TestClient):
        """questions_per_category 기본값(3) 동작 확인."""
        from slayer.schemas import InterviewQuestionsOutput

        mock_result = InterviewQuestionsOutput(
            questions=[],
            sample_answers=[],
            weak_areas=[],
            excluded_categories=[],
        )
        with patch(
            "slayer.pipelines.interview_questions.generate_interview_questions",
            return_value=mock_result,
        ) as mock_fn:
            response = client.post(
                "/api/v1/pipelines/interview",
                json={"jd": _jd_dict(), "resume": _resume_dict()},
            )

        assert response.status_code == 200
        # questions_per_category=3 (기본값)이 InterviewQuestionsInput에 전달됨
        call_args = mock_fn.call_args[0][0]  # 첫 번째 위치 인수 = input_data
        assert call_args.questions_per_category == 3
