"""Application status management endpoints.

Endpoints:
    POST   /api/v1/applications        — 새 지원 건 생성 (Apply Pipeline 실행)
    GET    /api/v1/applications        — 지원 현황 목록 (status/company 필터)
    PATCH  /api/v1/applications/{id}   — 상태 수동 변경
"""

from __future__ import annotations

import logging
import uuid
from typing import Optional

from fastapi import APIRouter, HTTPException, Query

logger = logging.getLogger(__name__)

from slayer.db.session import is_db_available
from slayer.pipelines.apply_pipeline.pipeline import ApplyError, apply
from slayer.schemas import ApplyRequest, ApplicationStatus

router = APIRouter(prefix="/applications", tags=["applications"])


@router.post("")
async def create_application(req: ApplyRequest):
    """지원 액션 실행.

    기업 UPSERT → applications INSERT → status_history 기록 → Calendar 등록(선택).
    DB 없어도 success:True 반환 (application_id는 None).
    """
    try:
        resp = apply(req)
    except ApplyError as e:
        raise HTTPException(status_code=500, detail=f"지원 처리 실패 ({e.stage}): {e.cause}")

    return resp.model_dump()


@router.get("")
async def list_applications(
    user_id: str = Query(..., description="사용자 UUID"),
    status: Optional[str] = Query(None, description="상태 필터 (scrapped|reviewing|applied|...)"),
    company: Optional[str] = Query(None, description="회사명 필터 (부분 일치)"),
):
    """지원 현황 목록 조회."""
    if not is_db_available():
        raise HTTPException(status_code=503, detail="DB 연결 없음")

    from slayer.db.models import Application, Company
    from slayer.db.session import get_session

    try:
        user_uuid = uuid.UUID(user_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="유효하지 않은 user_id 형식입니다.")

    with get_session() as session:
        q = session.query(Application).filter_by(user_id=user_uuid)

        if status:
            q = q.filter(Application.status == status)

        if company:
            q = q.join(Company).filter(Company.name.ilike(f"%{company}%"))

        apps = q.order_by(Application.created_at.desc()).limit(100).all()

        return [
            {
                "application_id": str(app.id),
                "company": app.company.name if app.company else None,
                "status": app.status,
                "ats_score": app.ats_score,
                "applied_at": app.applied_at.isoformat() if app.applied_at else None,
                "deadline": app.deadline.isoformat() if app.deadline else None,
                "created_at": app.created_at.isoformat() if app.created_at else None,
            }
            for app in apps
        ]


@router.patch("/{application_id}/status")
async def update_status(
    application_id: str,
    new_status: str,
    user_id: str = Query(...),
    note: Optional[str] = Query(None),
):
    """지원 상태 수동 변경.

    상태 전이 규칙 검증 후 applications + status_history 업데이트.
    """
    if not is_db_available():
        raise HTTPException(status_code=503, detail="DB 연결 없음")

    # 유효한 상태값 검증
    valid_statuses = {s.value for s in ApplicationStatus}
    if new_status not in valid_statuses:
        raise HTTPException(
            status_code=400,
            detail=f"유효하지 않은 상태: {new_status}. 허용: {valid_statuses}",
        )

    from slayer.db.models import Application, StatusHistory
    from slayer.db.session import get_session
    from slayer.services.status import validate_transition

    try:
        with get_session() as session:
            app = session.query(Application).filter_by(
                id=uuid.UUID(application_id)
            ).first()

            if not app:
                raise HTTPException(status_code=404, detail="지원 건을 찾을 수 없습니다.")

            try:
                validate_transition(app.status, new_status)
            except ValueError as e:
                raise HTTPException(status_code=400, detail=str(e))

            prev_status = app.status
            app.status = new_status

            session.add(StatusHistory(
                id=uuid.uuid4(),
                user_id=uuid.UUID(user_id),
                application_id=uuid.UUID(application_id),
                previous_status=prev_status,
                new_status=new_status,
                trigger_type="user_manual",
                triggered_by="user",
                note=note,
            ))

        return {
            "application_id": application_id,
            "previous_status": prev_status,
            "new_status": new_status,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error("지원 상태 변경 실패 (application_id=%s): %s", application_id, e)
        raise HTTPException(status_code=500, detail="지원 상태 변경 중 오류가 발생했습니다.")
