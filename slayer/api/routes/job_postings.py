"""Job postings 조회 엔드포인트."""
from __future__ import annotations

import uuid

from fastapi import APIRouter, HTTPException, Query

from slayer.db.session import is_db_available

router = APIRouter(prefix="/job-postings", tags=["job-postings"])


@router.get("")
async def list_job_postings(limit: int = Query(50, ge=1, le=200)):
    """최근 파싱된 JD 목록 조회."""
    if not is_db_available():
        raise HTTPException(status_code=503, detail="DB 연결 없음")

    from slayer.db.models import Company, JobPosting
    from slayer.db.session import get_session

    with get_session() as session:
        rows = (
            session.query(JobPosting)
            .order_by(JobPosting.created_at.desc())
            .limit(limit)
            .all()
        )
        return [
            {
                "id": str(r.id),
                "title": r.title,
                "position": r.position,
                "company": r.company.name if r.company else None,
                "deadline": r.deadline.isoformat() if r.deadline else None,
                "source_url": r.source_url,
                "created_at": r.created_at.isoformat() if r.created_at else None,
            }
            for r in rows
        ]


@router.get("/{job_posting_id}")
async def get_job_posting(job_posting_id: str):
    """JD 상세 조회 — parsed_data(JDSchema) 전체 반환."""
    if not is_db_available():
        raise HTTPException(status_code=503, detail="DB 연결 없음")

    try:
        job_uuid = uuid.UUID(job_posting_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="유효하지 않은 job_posting_id 형식입니다.")

    from slayer.db.models import JobPosting
    from slayer.db.session import get_session

    with get_session() as session:
        row = session.query(JobPosting).filter_by(id=job_uuid).first()

    if not row:
        raise HTTPException(status_code=404, detail="JD를 찾을 수 없습니다.")

    return {
        "id": str(row.id),
        "source_url": row.source_url,
        "parsed_data": row.parsed_data,
        "created_at": row.created_at.isoformat() if row.created_at else None,
    }
