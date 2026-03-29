"""파일 형식별 텍스트 추출.

PDF:  PyMuPDF (fitz)
DOCX: python-docx
MD/TXT/JSON: 직접 읽기
"""

from __future__ import annotations

from pathlib import Path

from slayer.pipelines.resume_parser.file_detector import FileFormat, ResumeFileError


def extract_text(file_path: str | Path, fmt: FileFormat) -> str:
    """파일에서 텍스트를 추출.

    Raises:
        ResumeFileError: 추출 실패 또는 빈 텍스트
    """
    path = Path(file_path)
    extractors = {
        FileFormat.PDF: _extract_pdf,
        FileFormat.DOCX: _extract_docx,
        FileFormat.MD: _extract_plain,
        FileFormat.TXT: _extract_plain,
        FileFormat.JSON: _extract_plain,
    }

    try:
        text = extractors[fmt](path)
    except ResumeFileError:
        raise
    except Exception as e:
        raise ResumeFileError(f"Failed to extract text from {path.name}: {e}") from e

    if not text or not text.strip():
        raise ResumeFileError(f"No text extracted from {path.name}")

    return text


def _extract_pdf(path: Path) -> str:
    """PyMuPDF로 PDF 텍스트 추출."""
    import fitz  # PyMuPDF

    text_parts: list[str] = []
    with fitz.open(str(path)) as doc:
        for page in doc:
            text_parts.append(page.get_text())
    return "\n".join(text_parts)


def _extract_docx(path: Path) -> str:
    """python-docx로 DOCX 텍스트 추출."""
    from docx import Document

    doc = Document(str(path))
    return "\n".join(para.text for para in doc.paragraphs)


def _extract_plain(path: Path) -> str:
    """MD/TXT 직접 읽기."""
    return path.read_text(encoding="utf-8")
