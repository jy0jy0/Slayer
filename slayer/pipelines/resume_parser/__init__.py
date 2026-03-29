"""이력서 파싱 파이프라인.

3단계: detect_format → extract_text → structurize
입력: 파일 경로 (PDF / DOCX / MD / TXT)
출력: ParsedResume (schemas.py)
"""

from __future__ import annotations

from pathlib import Path

from slayer.pipelines.resume_parser.extractors import extract_text
from slayer.pipelines.resume_parser.file_detector import (
    FileFormat,
    ResumeFileError,
    ResumeLLMError,
    ResumeParseError,
    detect_format,
)
from slayer.pipelines.resume_parser.structurizer import structurize
from slayer.schemas import ParsedResume

__all__ = [
    "parse_resume",
    "FileFormat",
    "ResumeParseError",
    "ResumeFileError",
    "ResumeLLMError",
]


def parse_resume(file_path: str | Path) -> ParsedResume:
    """파일 → ParsedResume. DB 무관 순수 함수.

    Args:
        file_path: 이력서 파일 경로

    Returns:
        ParsedResume: 구조화된 이력서 데이터

    Raises:
        ResumeFileError: 파일 읽기/형식 오류
        ResumeLLMError: LLM 호출 실패
    """
    fmt = detect_format(file_path)
    text = extract_text(file_path, fmt)
    return structurize(text, fmt.value)
