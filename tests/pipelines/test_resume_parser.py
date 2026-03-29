"""resume_parser 파이프라인 테스트.

단위 테스트 (오프라인):
    - file_detector: 형식 감지, 에러 케이스
    - extractors: PDF/TXT 텍스트 추출

E2E 테스트 (GOOGLE_API_KEY 필요):
    - structurizer: Gemini API 호출
    - parse_resume: 전체 파이프라인
"""

import os
from pathlib import Path

import pytest

from slayer.pipelines.resume_parser.file_detector import (
    FileFormat,
    ResumeFileError,
    detect_format,
)
from slayer.pipelines.resume_parser.extractors import extract_text

DATA_DIR = Path(__file__).resolve().parents[2] / "data" / "resumes"
SAMPLE_PDF = DATA_DIR / "backend_김준혁.pdf"

HAS_API_KEY = bool(os.environ.get("GOOGLE_API_KEY"))


# ── file_detector 테스트 ──────────────────────────────────


class TestDetectFormat:
    def test_pdf(self, tmp_path: Path):
        f = tmp_path / "test.pdf"
        f.write_bytes(b"%PDF-1.4")
        assert detect_format(f) == FileFormat.PDF

    def test_docx(self, tmp_path: Path):
        f = tmp_path / "test.docx"
        f.write_bytes(b"PK")
        assert detect_format(f) == FileFormat.DOCX

    def test_md(self, tmp_path: Path):
        f = tmp_path / "test.md"
        f.write_text("# Resume")
        assert detect_format(f) == FileFormat.MD

    def test_txt(self, tmp_path: Path):
        f = tmp_path / "test.txt"
        f.write_text("Resume")
        assert detect_format(f) == FileFormat.TXT

    def test_unsupported(self, tmp_path: Path):
        f = tmp_path / "test.xlsx"
        f.write_bytes(b"PK")
        with pytest.raises(ResumeFileError, match="Unsupported format"):
            detect_format(f)

    def test_not_found(self):
        with pytest.raises(ResumeFileError, match="File not found"):
            detect_format("/nonexistent/file.pdf")

    def test_directory(self, tmp_path: Path):
        with pytest.raises(ResumeFileError, match="Not a file"):
            detect_format(tmp_path)


# ── extractors 테스트 ──────────────────────────────────────


class TestExtractors:
    def test_extract_txt(self, tmp_path: Path):
        f = tmp_path / "resume.txt"
        f.write_text("홍길동\nPython Developer", encoding="utf-8")
        text = extract_text(f, FileFormat.TXT)
        assert "홍길동" in text
        assert "Python" in text

    def test_extract_md(self, tmp_path: Path):
        f = tmp_path / "resume.md"
        f.write_text("# 홍길동\n## Skills\n- Python", encoding="utf-8")
        text = extract_text(f, FileFormat.MD)
        assert "홍길동" in text

    def test_empty_file(self, tmp_path: Path):
        f = tmp_path / "empty.txt"
        f.write_text("")
        with pytest.raises(ResumeFileError, match="No text extracted"):
            extract_text(f, FileFormat.TXT)

    @pytest.mark.skipif(not SAMPLE_PDF.exists(), reason="Sample PDF not found")
    def test_extract_pdf(self):
        text = extract_text(SAMPLE_PDF, FileFormat.PDF)
        assert len(text) > 100


# ── E2E 테스트 (API 키 필요) ──────────────────────────────


@pytest.mark.skipif(not HAS_API_KEY, reason="GOOGLE_API_KEY not set")
class TestE2E:
    @pytest.mark.skipif(not SAMPLE_PDF.exists(), reason="Sample PDF not found")
    def test_parse_resume_pdf(self):
        from slayer.pipelines.resume_parser import parse_resume

        result = parse_resume(SAMPLE_PDF)
        assert result.personal_info.name
        assert result.source_format == "pdf"

    def test_parse_resume_txt(self, tmp_path: Path):
        from slayer.pipelines.resume_parser import parse_resume

        f = tmp_path / "resume.txt"
        f.write_text(
            "이름: 홍길동\n이메일: hong@example.com\n"
            "경력: 네이버 백엔드 개발자 2020-03 ~ 2023-06\n"
            "스킬: python, java, aws\n"
            "학력: 서울대학교 컴퓨터공학과 학사 2016-03 ~ 2020-02",
            encoding="utf-8",
        )
        result = parse_resume(f)
        assert result.personal_info.name
        assert result.source_format == "txt"
