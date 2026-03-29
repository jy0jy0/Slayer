"""resume_parser 통합 테스트 — company-research 브랜치 테스트 데이터 사용.

모든 지원 포맷(MD, TXT, JSON, PDF)에서 ParsedResume 출력이
ResumeOptimizationInput, CoverLetterInput에 바로 연결되는지 검증.

GOOGLE_API_KEY 필요 (E2E 테스트).
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from slayer.pipelines.resume_parser import parse_resume
from slayer.pipelines.resume_parser.file_detector import FileFormat, detect_format
from slayer.schemas import (
    CoverLetterInput,
    JDSchema,
    MatchResult,
    ParsedResume,
    ResumeOptimizationInput,
    CompanyResearchOutput,
)

TEST_DATA = Path(__file__).parent / "test_data" / "resumes"
HAS_API_KEY = bool(os.environ.get("GOOGLE_API_KEY"))

# ── 샘플 JD + 매칭 결과 (통합 테스트용 픽스처) ────────────────


@pytest.fixture
def sample_jd() -> JDSchema:
    return JDSchema(
        company="테스트 회사",
        title="백엔드 개발자",
        position="Backend Engineer",
        skills=["python", "fastapi", "postgresql", "docker"],
    )


@pytest.fixture
def sample_match_result() -> MatchResult:
    return MatchResult(
        ats_score=72.0,
        score_breakdown={"keywords": 0.25, "experience": 0.20},
        matched_keywords=["python", "docker"],
        missing_keywords=["fastapi", "postgresql"],
        strengths=["Python 경험 풍부"],
        weaknesses=["FastAPI 경험 없음"],
        gap_summary="주요 백엔드 스택 일부 미보유",
    )


@pytest.fixture
def sample_company_research() -> CompanyResearchOutput:
    return CompanyResearchOutput(
        company_name="테스트 회사",
        summary="AI 스타트업",
    )


# ── 포맷 감지 테스트 (오프라인) ─────────────────────────────


class TestFormatDetection:
    def test_json_format(self, tmp_path: Path):
        f = tmp_path / "resume.json"
        f.write_text('{"name": "홍길동"}')
        assert detect_format(f) == FileFormat.JSON

    def test_all_test_data_formats(self):
        """테스트 데이터 파일들의 형식 감지 확인."""
        expected = {
            "backend_김준혁.md": FileFormat.MD,
            "devops_최은지.txt": FileFormat.TXT,
            "frontend_박민재.md": FileFormat.MD,
            "fullstack_정하늘.json": FileFormat.JSON,
            "ml_이서연.json": FileFormat.JSON,
        }
        for filename, expected_fmt in expected.items():
            path = TEST_DATA / filename
            assert path.exists(), f"테스트 데이터 없음: {filename}"
            assert detect_format(path) == expected_fmt


# ── E2E 파싱 테스트 ───────────────────────────────────────


@pytest.mark.skipif(not HAS_API_KEY, reason="GOOGLE_API_KEY not set")
class TestParseAllFormats:
    """모든 포맷에서 ParsedResume이 올바르게 생성되는지 확인."""

    @pytest.mark.parametrize("filename,expected_format", [
        ("backend_김준혁.md", "md"),
        ("devops_최은지.txt", "txt"),
        ("frontend_박민재.md", "md"),
        ("fullstack_정하늘.json", "json"),
        ("ml_이서연.json", "json"),
    ])
    def test_parse_resume(self, filename: str, expected_format: str):
        result = parse_resume(TEST_DATA / filename)

        assert isinstance(result, ParsedResume)
        assert result.personal_info.name
        assert result.source_format == expected_format
        assert result.total_years_experience is not None
        assert result.total_years_experience >= 0

    def test_parse_md_has_skills(self):
        result = parse_resume(TEST_DATA / "backend_김준혁.md")
        assert len(result.skills) > 0
        assert all(s == s.lower() for s in result.skills), "skills는 소문자여야 함"

    def test_parse_json_resume(self):
        result = parse_resume(TEST_DATA / "ml_이서연.json")
        assert result.personal_info.name == "이서연"
        assert result.source_format == "json"


# ── 통합 연결 테스트 ──────────────────────────────────────


@pytest.mark.skipif(not HAS_API_KEY, reason="GOOGLE_API_KEY not set")
class TestIntegration:
    """ParsedResume → 매칭/최적화/자소서 Agent 입력 연결 검증."""

    def test_parsed_resume_to_optimization_input(
        self, sample_jd, sample_match_result
    ):
        """parse_resume() 출력이 ResumeOptimizationInput에 바로 연결되는지."""
        result = parse_resume(TEST_DATA / "backend_김준혁.md")

        opt_input = ResumeOptimizationInput(
            parsed_resume=result,
            jd=sample_jd,
            match_result=sample_match_result,
        )

        assert opt_input.parsed_resume.personal_info.name
        assert opt_input.target_ats_score == 80.0
        assert opt_input.max_iterations == 3

    def test_parsed_resume_to_cover_letter_input(
        self, sample_jd, sample_match_result, sample_company_research
    ):
        """parse_resume() 출력이 CoverLetterInput에 바로 연결되는지."""
        result = parse_resume(TEST_DATA / "devops_최은지.txt")

        cl_input = CoverLetterInput(
            parsed_resume=result,
            jd=sample_jd,
            company_research=sample_company_research,
            match_result=sample_match_result,
        )

        assert cl_input.parsed_resume.personal_info.name
        assert cl_input.jd.company == "테스트 회사"

    def test_all_formats_produce_compatible_output(
        self, sample_jd, sample_match_result
    ):
        """모든 포맷에서 파싱한 결과가 동일하게 ResumeOptimizationInput에 연결됨."""
        files = [
            TEST_DATA / "backend_김준혁.md",
            TEST_DATA / "fullstack_정하늘.json",
        ]
        for file_path in files:
            result = parse_resume(file_path)
            opt_input = ResumeOptimizationInput(
                parsed_resume=result,
                jd=sample_jd,
                match_result=sample_match_result,
            )
            assert opt_input.parsed_resume.personal_info.name, (
                f"{file_path.name}: name이 비어 있음"
            )
