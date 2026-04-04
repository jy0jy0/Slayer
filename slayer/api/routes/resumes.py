"""Resume upload and parsing endpoints.

Endpoints:
    POST /api/v1/resumes/upload — 이력서 업로드 + OCR 파싱
    GET  /api/v1/resumes/{id}   — 파싱 결과 조회
"""

from __future__ import annotations

import tempfile
import uuid
from pathlib import Path

from fastapi import APIRouter, HTTPException, UploadFile, File, Form

from slayer.db import repository
from slayer.db.session import is_db_available
from slayer.pipelines.resume_parser import parse_resume
from slayer.pipelines.resume_parser.file_detector import ResumeFileError, ResumeLLMError

router = APIRouter(prefix="/resumes", tags=["resumes"])

_ALLOWED_EXTENSIONS = {".pdf", ".docx", ".md", ".txt", ".json"}


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
        raise HTTPException(
            status_code=400,
            detail=f"지원하지 않는 파일 형식: {suffix}. 허용: {_ALLOWED_EXTENSIONS}",
        )

    # 임시 파일에 저장 후 파싱
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
        tmp.write(await file.read())
        tmp_path = Path(tmp.name)

    try:
        parsed = parse_resume(tmp_path)
    except ResumeFileError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except ResumeLLMError as e:
        raise HTTPException(status_code=502, detail=f"LLM 파싱 실패: {e}")
    finally:
        tmp_path.unlink(missing_ok=True)

    # DB 저장 (fail-safe — DB 없어도 파싱 결과는 반환)
    resume_row = repository.save_parsed_resume(
        user_id=user_id,
        file_name=file.filename or "resume",
        file_type=suffix.lstrip("."),
        file_url="",          # Supabase Storage 연동 시 URL 업데이트
        parsed_resume=parsed,
    )
    resume_id = str(resume_row.id) if resume_row else None

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
        "created_at": row.created_at.isoformat() if row.created_at else None,
    }
