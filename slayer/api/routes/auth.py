"""Google OAuth 토큰 저장 엔드포인트.

Supabase는 Google provider token을 DB에 자동 저장하지 않는다.
프론트엔드가 로그인 직후 session.provider_token 을 이 엔드포인트로 전송하면
백엔드가 public.users 에 저장하여 Gmail / Calendar API 호출에 사용한다.

Endpoint:
    POST /api/v1/auth/google-token  — Google OAuth 토큰 저장
    GET  /api/v1/auth/google-token  — 토큰 저장 여부 확인
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from slayer.db.session import is_db_available

router = APIRouter(prefix="/auth", tags=["auth"])


class GoogleTokenRequest(BaseModel):
    """Google OAuth 토큰 저장 요청.

    프론트엔드에서 supabase.auth.onAuthStateChange 콜백으로 받은 값을 전송.

    Fields:
        user_id:        public.users UUID (Supabase auth.users.id 와 동일)
        access_token:   Google OAuth access token (session.provider_token)
        refresh_token:  Google OAuth refresh token (session.provider_refresh_token, 선택)
        expires_at:     access token 만료 시각 ISO8601 (선택)
    """

    user_id: str
    access_token: str
    refresh_token: Optional[str] = None
    expires_at: Optional[str] = None  # ISO8601


@router.post("/google-token", status_code=200)
async def save_google_token(req: GoogleTokenRequest):
    """Google OAuth 토큰을 public.users 에 저장.

    Supabase OAuth 로그인 직후 프론트에서 한 번 호출.
    이후 Gmail / Calendar API 호출 시 이 토큰을 사용.
    """
    if not is_db_available():
        raise HTTPException(status_code=503, detail="DB 연결 없음")

    from slayer.db.models import User
    from slayer.db.session import get_session

    try:
        user_uuid = uuid.UUID(req.user_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="유효하지 않은 user_id 형식")

    expires_at: datetime | None = None
    if req.expires_at:
        try:
            expires_at = datetime.fromisoformat(req.expires_at)
        except ValueError:
            raise HTTPException(status_code=400, detail="유효하지 않은 expires_at 형식 (ISO8601 필요)")

    try:
        with get_session() as session:
            user = session.query(User).filter_by(id=user_uuid).first()
            if not user:
                raise HTTPException(status_code=404, detail="사용자를 찾을 수 없습니다.")

            user.google_access_token = req.access_token
            if req.refresh_token:
                user.google_refresh_token = req.refresh_token
            if expires_at:
                user.token_expires_at = expires_at
            user.updated_at = datetime.now(timezone.utc)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"토큰 저장 실패: {e}")

    return {
        "success": True,
        "user_id": req.user_id,
        "has_refresh_token": req.refresh_token is not None,
        "expires_at": req.expires_at,
    }


@router.get("/google-token")
async def check_google_token(user_id: str):
    """Google 토큰 저장 여부 확인.

    access_token 값 자체는 반환하지 않고 저장 여부와 만료 시각만 반환.
    """
    if not is_db_available():
        raise HTTPException(status_code=503, detail="DB 연결 없음")

    from slayer.db.models import User
    from slayer.db.session import get_session

    try:
        user_uuid = uuid.UUID(user_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="유효하지 않은 user_id 형식")

    try:
        with get_session() as session:
            user = session.query(User).filter_by(id=user_uuid).first()
            if not user:
                raise HTTPException(status_code=404, detail="사용자를 찾을 수 없습니다.")

            return {
                "user_id": user_id,
                "has_access_token": bool(user.google_access_token),
                "has_refresh_token": bool(user.google_refresh_token),
                "token_expires_at": user.token_expires_at.isoformat() if user.token_expires_at else None,
            }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
