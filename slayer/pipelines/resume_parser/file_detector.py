"""파일 형식 감지 + 예외 계층.

예외 계층:
    ResumeParseError          — 기본 예외
    ├── ResumeFileError       — 파일 읽기/형식 오류
    └── ResumeLLMError        — LLM 호출 실패
"""

from __future__ import annotations

from enum import Enum
from pathlib import Path


# ── 예외 계층 ──────────────────────────────────────────────


class ResumeParseError(Exception):
    """이력서 파싱 기본 예외."""


class ResumeFileError(ResumeParseError):
    """파일 읽기 또는 형식 오류."""


class ResumeLLMError(ResumeParseError):
    """LLM 호출 실패.

    Attributes:
        stage: 실패 단계 (e.g. "structurize")
        cause: 원인 예외
    """

    def __init__(self, stage: str, cause: Exception | None = None):
        self.stage = stage
        self.cause = cause
        msg = f"LLM failed at stage '{stage}'"
        if cause:
            msg += f": {cause}"
        super().__init__(msg)


# ── 파일 형식 ──────────────────────────────────────────────


class FileFormat(str, Enum):
    PDF = "pdf"
    DOCX = "docx"
    MD = "md"
    TXT = "txt"


_EXT_MAP: dict[str, FileFormat] = {
    ".pdf": FileFormat.PDF,
    ".docx": FileFormat.DOCX,
    ".md": FileFormat.MD,
    ".txt": FileFormat.TXT,
}


def detect_format(file_path: str | Path) -> FileFormat:
    """파일 경로에서 형식을 감지.

    Raises:
        ResumeFileError: 파일이 없거나 지원하지 않는 형식
    """
    path = Path(file_path)

    if not path.exists():
        raise ResumeFileError(f"File not found: {path}")

    if not path.is_file():
        raise ResumeFileError(f"Not a file: {path}")

    ext = path.suffix.lower()
    fmt = _EXT_MAP.get(ext)
    if fmt is None:
        raise ResumeFileError(
            f"Unsupported format: '{ext}'. Supported: {list(_EXT_MAP.keys())}"
        )
    return fmt
