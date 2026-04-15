"""Resume upload and parsing endpoints.

Endpoints:
    POST /api/v1/resumes/upload — 이력서 업로드 + OCR 파싱
    GET  /api/v1/resumes/{id}   — 파싱 결과 조회
"""

from __future__ import annotations

import tempfile
import uuid
from pathlib import Path

from fastapi import APIRouter, File, Form, HTTPException, UploadFile

from slayer.db import repository
from slayer.db.session import is_db_available
from slayer.pipelines.resume_parser import parse_resume
from slayer.pipelines.resume_parser.file_detector import ResumeFileError, ResumeLLMError

router = APIRouter(prefix="/resumes", tags=["resumes"])

_ALLOWED_EXTENSIONS = {".pdf", ".docx", ".md", ".txt", ".json"}


def _is_probably_scanned_pdf(file_error_msg: str, suffix: str) -> bool:
    """Heuristic: PDF인데 텍스트 추출이 안 되는 경우 스캔본일 확률이 높다."""
    if suffix != ".pdf":
        return False
    msg = (file_error_msg or "").lower()
    return (
        "no text extracted" in msg or "failed to extract text" in msg or "empty" in msg
    )


def _resume_file_error_to_detail(e: ResumeFileError, suffix: str) -> str:
    """사용자 친화적인 파일 오류 메시지 변환."""
    msg = str(e)

    if _is_probably_scanned_pdf(msg, suffix):
        return (
            "PDF에서 텍스트를 추출하지 못했습니다. "
            "이미지 기반(스캔본) PDF일 수 있습니다. "
            "텍스트 선택이 가능한 PDF 또는 DOCX 파일로 다시 업로드해 주세요."
        )

    if "unsupported format" in msg.lower() or "지원하지 않는 파일 형식" in msg:
        allowed = ", ".join(
            sorted(ext.lstrip(".").upper() for ext in _ALLOWED_EXTENSIONS)
        )
        return f"지원하지 않는 파일 형식입니다. 지원 형식: {allowed}"

    if "file not found" in msg.lower():
        return "업로드된 파일을 찾을 수 없습니다. 다시 시도해 주세요."

    return f"이력서 파일 처리 중 오류가 발생했습니다: {msg}"


@router.post("/upload")
async def upload_resume(
    file: UploadFile = File(...),
    user_id: str = Form(...),
):
    """이력서 파일 업로드 + 파싱.

    - 지원 포맷: PDF, DOCX, MD, TXT, JSON
    - GOOGLE_API_KEY → Gemini 파싱 / OPENAI_API_KEY → OpenAI 파싱
    - DB 없어도 파싱 결과 반환 (저장만 skip)
    """
    suffix = Path(file.filename or "resume").suffix.lower()
    if suffix not in _ALLOWED_EXTENSIONS:
        allowed = ", ".join(
            sorted(ext.lstrip(".").upper() for ext in _ALLOWED_EXTENSIONS)
        )
        raise HTTPException(
            status_code=400,
            detail=f"지원하지 않는 파일 형식: {suffix or '(없음)'} (지원 형식: {allowed})",
        )

    # 임시 파일에 저장 후 파싱
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
        tmp.write(await file.read())
        tmp_path = Path(tmp.name)

    try:
        parsed = parse_resume(tmp_path)
    except ResumeFileError as e:
        raise HTTPException(
            status_code=400, detail=_resume_file_error_to_detail(e, suffix)
        )
    except ResumeLLMError as e:
        # 내부 파서 단계 실패를 사용자에게 이해 가능한 메시지로 전달
        # (상세 내부 스택은 노출하지 않음)
        raise HTTPException(
            status_code=502,
            detail=(
                f"이력서 구조화(LLM) 단계에서 실패했습니다. "
                f"잠시 후 다시 시도해 주세요. (stage={e.stage})"
            ),
        )
    except Exception as e:
        # 예상치 못한 파서 내부 오류 — 전체 traceback 로깅 후 사용자에게는 간략히 전달
        import traceback as _tb
        logger.error("이력서 파싱 예외 (file=%s): %s\n%s", file.filename, e, _tb.format_exc())
        raise HTTPException(
            status_code=500,
            detail=(
                "이력서 파싱 중 내부 오류가 발생했습니다. "
                "파일 형식/손상 여부를 확인한 뒤 다시 시도해 주세요."
            ),
        )
    finally:
        tmp_path.unlink(missing_ok=True)

    # DB 저장 (fail-safe — DB 없어도 파싱 결과는 반환)
    saved_id = repository.save_parsed_resume(
        user_id=user_id,
        file_name=file.filename or "resume",
        file_type=suffix.lstrip("."),
        file_url="",  # Supabase Storage 연동 시 URL 업데이트
        parsed_resume=parsed,
    )
    resume_id = str(saved_id) if saved_id else None

    return {
        "resume_id": resume_id,
        "parsed": parsed.model_dump(),
        "saved_to_db": resume_id is not None,
    }


@router.get("/{resume_id}")
async def get_resume(resume_id: str):
    """파싱된 이력서 조회."""
    if not is_db_available():
        raise HTTPException(status_code=503, detail="DB 연결 없음")

    from slayer.db.models import Resume
    from slayer.db.session import get_session

    with get_session() as session:
        row = session.query(Resume).filter_by(id=uuid.UUID(resume_id)).first()

    if not row:
        raise HTTPException(status_code=404, detail="이력서를 찾을 수 없습니다.")

    return {
        "resume_id": resume_id,
        "file_name": row.file_name,
        "source_format": row.source_format,
        "parse_status": row.parse_status,
        "parsed": row.parsed_data,
        "created_at": row.created_at.isoformat()
        if row.created_at is not None
        else None,
    }
