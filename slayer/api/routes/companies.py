"""Companies 조회 엔드포인트."""
from __future__ import annotations

import uuid

from fastapi import APIRouter, HTTPException, Query

from slayer.db.session import is_db_available

router = APIRouter(prefix="/companies", tags=["companies"])


@router.get("")
async def list_companies(limit: int = Query(100, ge=1, le=500)):
    """리서치된 기업 목록 조회."""
    if not is_db_available():
        raise HTTPException(status_code=503, detail="DB 연결 없음")

    from slayer.db.models import Company
    from slayer.db.session import get_session

    with get_session() as session:
        rows = (
            session.query(Company)
            .order_by(Company.researched_at.desc().nullslast())
            .limit(limit)
            .all()
        )
        return [
            {
                "id": str(r.id),
                "name": r.name,
                "industry": r.industry,
                "employee_count": r.employee_count,
                "researched_at": r.researched_at.isoformat() if r.researched_at else None,
            }
            for r in rows
        ]


@router.get("/{company_id}")
async def get_company(company_id: str):
    """기업 리서치 상세 조회."""
    if not is_db_available():
        raise HTTPException(status_code=503, detail="DB 연결 없음")

    try:
        company_uuid = uuid.UUID(company_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="유효하지 않은 company_id 형식입니다.")

    from slayer.db.models import Company
    from slayer.db.session import get_session

    with get_session() as session:
        row = session.query(Company).filter_by(id=company_uuid).first()

    if not row:
        raise HTTPException(status_code=404, detail="기업 정보를 찾을 수 없습니다.")

    return {
        "id": str(row.id),
        "name": row.name,
        "name_en": row.name_en,
        "industry": row.industry,
        "ceo": row.ceo,
        "founded_date": row.founded_date,
        "employee_count": row.employee_count,
        "headquarters": row.headquarters,
        "summary": row.summary,
        "basic_info": row.basic_info,
        "financial_info": row.financial_info,
        "recent_news": row.recent_news,
        "researched_at": row.researched_at.isoformat() if row.researched_at else None,
    }
