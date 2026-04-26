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
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

from slayer.db.session import is_db_available

router = APIRouter(prefix="/auth", tags=["auth"])

_STREAMLIT_URL = "http://localhost:8501"

_CALLBACK_HTML = """<!DOCTYPE html>
<html>
<head><meta charset="utf-8"><title>로그인 중...</title></head>
<body>
<script src="https://cdn.jsdelivr.net/npm/@supabase/supabase-js@2"></script>
<script>
(function () {{
    var SUPABASE_URL  = '{supabase_url}';
    var SUPABASE_KEY  = '{supabase_anon_key}';
    var STREAMLIT_URL = '{streamlit_url}';

    function forwardTokens(access_token, provider_token, provider_refresh_token, refresh_token, expires_at) {{
        var qs = new URLSearchParams({{
            access_token:           access_token           || '',
            provider_token:         provider_token         || '',
            provider_refresh_token: provider_refresh_token || '',
            refresh_token:          refresh_token          || '',
            expires_at:             expires_at             || '',
        }});
        window.location.replace(STREAMLIT_URL + '/?' + qs.toString());
    }}

    // ── PKCE flow: ?code=... ──────────────────────────────
    var urlParams = new URLSearchParams(window.location.search);
    var code = urlParams.get('code');
    if (code) {{
        var client = window.supabase.createClient(SUPABASE_URL, SUPABASE_KEY);
        client.auth.exchangeCodeForSession(code).then(function(result) {{
            var session = result.data && result.data.session;
            if (session) {{
                forwardTokens(
                    session.access_token,
                    session.provider_token         || '',
                    session.provider_refresh_token || '',
                    session.refresh_token,
                    session.expires_at ? String(session.expires_at) : ''
                );
            }} else {{
                window.location.replace(STREAMLIT_URL);
            }}
        }});
        return;
    }}

    // ── Implicit flow: #access_token=... ──────────────────
    var hash = window.location.hash;
    if (hash && hash.includes('access_token')) {{
        var params = new URLSearchParams(hash.substring(1));
        forwardTokens(
            params.get('access_token'),
            params.get('provider_token'),
            params.get('provider_refresh_token'),
            params.get('refresh_token'),
            params.get('expires_at')
        );
        return;
    }}

    // 토큰 없음 → 로그인 페이지로
    window.location.replace(STREAMLIT_URL);
}})();
</script>
<p style="font-family:sans-serif;text-align:center;padding-top:40px;color:#888">로그인 처리 중...</p>
</body>
</html>
"""


def _build_callback_html() -> str:
    from slayer.config import SUPABASE_URL, SUPABASE_ANON_KEY
    return _CALLBACK_HTML.format(
        supabase_url=SUPABASE_URL,
        supabase_anon_key=SUPABASE_ANON_KEY,
        streamlit_url=_STREAMLIT_URL,
    )


@router.get("/callback", response_class=HTMLResponse, include_in_schema=False)
async def oauth_callback():
    """Supabase OAuth 콜백 중간 페이지.

    Implicit flow: Supabase → /auth/callback#access_token=... → JS → localhost:8501/?access_token=...
    PKCE flow:     Supabase → /auth/callback?code=...         → JS(SDK 교환) → localhost:8501/?access_token=...
    """
    return HTMLResponse(content=_build_callback_html())


class GoogleTokenRequest(BaseModel):
    """Google OAuth 토큰 저장 요청.

    프론트엔드에서 supabase.auth.onAuthStateChange 콜백으로 받은 값을 전송.

    Fields:
        user_id:                public.users UUID (Supabase auth.users.id 와 동일)
        access_token:           Google OAuth access token (session.provider_token)
        refresh_token:          Google OAuth refresh token (session.provider_refresh_token, 선택)
        expires_at:             access token 만료 시각 ISO8601 (선택)
        email:                  사용자 이메일 (최초 로그인 시 users 레코드 자동 생성에 사용)
        name:                   사용자 이름 (최초 로그인 시 users 레코드 자동 생성에 사용)
        google_id:              Google sub / provider_id (최초 로그인 시 사용)
        supabase_refresh_token: Supabase 세션 refresh_token (토큰 자동 갱신에 사용)
    """

    user_id: str
    access_token: str
    refresh_token: Optional[str] = None
    expires_at: Optional[str] = None  # ISO8601
    # 최초 로그인 시 public.users 자동 생성용
    email: Optional[str] = None
    name: Optional[str] = None
    google_id: Optional[str] = None
    supabase_refresh_token: Optional[str] = None


@router.post("/google-token", status_code=200)
async def save_google_token(req: GoogleTokenRequest):
    """Google OAuth 토큰을 public.users 에 저장.

    Supabase OAuth 로그인 직후 프론트에서 한 번 호출.
    users 레코드가 없으면 자동 생성 (email, name, google_id 필요).
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

    created = False
    try:
        with get_session() as session:
            user = session.query(User).filter_by(id=user_uuid).first()
            if not user:
                # 최초 Google OAuth 로그인 — public.users 레코드 자동 생성
                if not req.email or not req.google_id:
                    raise HTTPException(
                        status_code=404,
                        detail="사용자를 찾을 수 없습니다. email과 google_id를 함께 전송해 주세요.",
                    )
                user = User(
                    id=user_uuid,
                    google_id=req.google_id,
                    email=req.email,
                    name=req.name or req.email.split("@")[0],
                )
                session.add(user)
                created = True

            user.google_access_token = req.access_token
            if req.refresh_token:
                user.google_refresh_token = req.refresh_token
            if req.supabase_refresh_token:
                user.supabase_refresh_token = req.supabase_refresh_token
            if expires_at:
                user.token_expires_at = expires_at
            user.updated_at = datetime.now(timezone.utc)

    except HTTPException:
        raise
    except Exception as e:
        logger.error("토큰 저장 실패 (user_id=%s): %s", req.user_id, e)
        raise HTTPException(status_code=500, detail="토큰 저장 중 오류가 발생했습니다.")

    return {
        "success": True,
        "user_id": req.user_id,
        "created": created,
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
