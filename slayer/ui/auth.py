"""Streamlit Google OAuth 인증 헬퍼.

Supabase OAuth 흐름:
    1. get_oauth_url() 로 Google 로그인 URL 생성
    2. 사용자가 로그인 → Supabase가 localhost:8501/#access_token=...&provider_token=... 로 리다이렉트
    3. JS가 hash → query param 변환 (Streamlit은 hash 직접 못 읽음)
    4. handle_oauth_callback() 로 query param 읽어 DB 저장 + session_state 세팅
"""

from __future__ import annotations

import json
import base64
import logging
import uuid
from datetime import datetime, timezone
from urllib.parse import urlencode

import streamlit as st

logger = logging.getLogger(__name__)

# Supabase 프로젝트 설정
_SUPABASE_URL = "https://mwahcudydbkjjtlfgubr.supabase.co"
_REDIRECT_URL = "http://localhost:8000/api/v1/auth/callback"  # FastAPI 중간 페이지 (hash → query param 변환)


def get_oauth_url() -> str:
    """Google OAuth 로그인 URL 반환."""
    params = urlencode({
        "provider": "google",
        "redirect_to": _REDIRECT_URL,
        "scopes": "email profile https://www.googleapis.com/auth/gmail.readonly https://www.googleapis.com/auth/calendar",
        "access_type": "offline",
        "prompt": "consent",  # 매번 consent → refresh_token 항상 발급
    })
    return f"{_SUPABASE_URL}/auth/v1/authorize?{params}"


def inject_hash_to_query_params() -> None:
    """URL hash를 query param으로 변환하는 JS 주입.

    Supabase OAuth 콜백은 hash fragment로 토큰을 전달.
    Streamlit은 hash를 읽을 수 없어 JS로 query param으로 변환.
    """
    st.components.v1.html("""
    <script>
    (function() {
        // OAuth 콜백은 부모 창 URL hash에 붙어옴 (#access_token=...)
        const hash = window.parent.location.hash;
        if (!hash || !hash.includes('access_token')) return;

        const params = new URLSearchParams(hash.substring(1));
        const accessToken   = params.get('access_token')   || '';
        const refreshToken  = params.get('refresh_token')  || '';
        const providerToken = params.get('provider_token') || '';
        const expiresAt     = params.get('expires_at')     || '';

        if (accessToken) {
            const newUrl = window.parent.location.pathname
                + '?access_token='   + encodeURIComponent(accessToken)
                + '&refresh_token='  + encodeURIComponent(refreshToken)
                + '&provider_token=' + encodeURIComponent(providerToken)
                + '&expires_at='     + encodeURIComponent(expiresAt);
            window.parent.location.replace(newUrl);
        }
    })();
    </script>
    """, height=0)


def _decode_jwt_payload(token: str) -> dict:
    """JWT payload를 검증 없이 디코딩 (user_id 추출용)."""
    try:
        payload_b64 = token.split('.')[1]
        # base64 패딩 보정
        payload_b64 += '=' * (4 - len(payload_b64) % 4)
        return json.loads(base64.b64decode(payload_b64))
    except Exception:
        return {}


def _save_token_to_db(
    user_id: str,
    access_token: str,
    provider_token: str,
    supabase_refresh_token: str,
    expires_at: str,
    provider_refresh_token: str = "",
) -> bool:
    """Google/Supabase 토큰을 public.users 테이블에 저장.

    Args:
        supabase_refresh_token: Supabase refresh_token (토큰 자동 갱신용)
        provider_refresh_token: Google OAuth refresh_token (있을 경우 저장)
    """
    try:
        from slayer.db.models import User
        from slayer.db.session import get_session, is_db_available

        if not is_db_available():
            logger.warning("DB 없음 — 토큰 저장 건너뜀")
            return False

        exp_dt: datetime | None = None
        if expires_at:
            try:
                exp_dt = datetime.fromtimestamp(int(expires_at), tz=timezone.utc)
            except (ValueError, TypeError):
                try:
                    exp_dt = datetime.fromisoformat(expires_at)
                except ValueError:
                    pass

        with get_session() as session:
            user = session.query(User).filter_by(id=uuid.UUID(user_id)).first()
            if not user:
                logger.warning("user_id %s 없음", user_id)
                return False
            user.google_access_token = provider_token or access_token
            # Supabase refresh_token: 자동 갱신에 사용
            if supabase_refresh_token:
                user.supabase_refresh_token = supabase_refresh_token
            # Google refresh_token: provider_refresh_token이 있을 때만 저장
            if provider_refresh_token:
                user.google_refresh_token = provider_refresh_token
            if exp_dt:
                user.token_expires_at = exp_dt
            user.updated_at = datetime.now(timezone.utc)

        return True
    except Exception as e:
        logger.error("토큰 DB 저장 실패: %s", e)
        return False


def handle_oauth_callback() -> bool:
    """OAuth 콜백 query param 처리.

    Returns:
        True: 새로 로그인 완료
        False: 콜백 없음 (일반 페이지 로드)
    """
    params = st.query_params
    access_token = params.get("access_token", "")
    if not access_token:
        return False

    provider_token          = params.get("provider_token", "")
    provider_refresh_token  = params.get("provider_refresh_token", "")
    refresh_token           = params.get("refresh_token", "")
    expires_at              = params.get("expires_at", "")

    logger.info("OAuth 콜백 수신 — provider_token=%s... provider_refresh_token=%s... refresh_token=%s...",
                provider_token[:20] if provider_token else "없음",
                provider_refresh_token[:20] if provider_refresh_token else "없음",
                refresh_token[:20] if refresh_token else "없음")

    # JWT에서 user_id(sub) 추출
    payload = _decode_jwt_payload(access_token)
    user_id  = payload.get("sub", "")
    email    = payload.get("email", "")

    if not user_id:
        st.error("토큰에서 user_id를 읽을 수 없습니다.")
        return False

    # DB 저장: google_access_token + supabase_refresh_token (자동 갱신용)
    saved = _save_token_to_db(
        user_id,
        access_token,
        provider_token,
        supabase_refresh_token=refresh_token,
        expires_at=expires_at,
        provider_refresh_token=provider_refresh_token,
    )

    # session_state에 로그인 정보 기록
    st.session_state["user_id"]      = user_id
    st.session_state["email"]        = email
    st.session_state["access_token"] = access_token
    st.session_state["logged_in"]    = True
    st.session_state["token_saved"]  = saved

    # 새로고침 후에도 세션 유지: uid만 URL에 남김
    st.query_params.clear()
    st.query_params["uid"] = user_id
    return True


def restore_session() -> bool:
    """새로고침 후 uid query param으로 세션 복원.

    Returns:
        True: 복원 성공
        False: uid 없거나 DB 조회 실패
    """
    if st.session_state.get("logged_in"):
        return True  # 이미 로그인 상태

    uid = st.query_params.get("uid", "")
    if not uid:
        return False

    try:
        from slayer.db.models import User
        from slayer.db.session import get_session, is_db_available

        if not is_db_available():
            return False

        with get_session() as session:
            user = session.query(User).filter_by(id=uuid.UUID(uid)).first()
            if not user:
                return False
            st.session_state["user_id"]     = str(user.id)
            st.session_state["email"]       = user.email or ""
            st.session_state["logged_in"]   = True
            st.session_state["token_saved"] = bool(user.google_access_token)
        return True
    except Exception:
        return False


def is_logged_in() -> bool:
    return st.session_state.get("logged_in", False)


def _call_supabase_auth(endpoint: str, payload: dict) -> dict:
    """Supabase auth REST API 호출."""
    import urllib.request
    import json as _json
    from slayer.config import SUPABASE_ANON_KEY

    url = f"{_SUPABASE_URL}/auth/v1/{endpoint}"
    data = _json.dumps(payload).encode()
    req = urllib.request.Request(
        url, data=data,
        headers={"apikey": SUPABASE_ANON_KEY, "Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return _json.loads(resp.read())
    except urllib.error.HTTPError as e:
        try:
            return _json.loads(e.read())
        except Exception:
            return {"error": str(e)}
    except Exception as e:
        return {"error": str(e)}


def _ensure_user_exists(user_id: str, email: str) -> str:
    """public.users에 없으면 생성. 같은 이메일 기존 레코드 있으면 그 ID 반환."""
    try:
        from slayer.db.models import User
        from slayer.db.session import get_session, is_db_available

        if not is_db_available():
            return user_id

        with get_session() as session:
            # UUID로 먼저 조회
            user = session.query(User).filter_by(id=uuid.UUID(user_id)).first()
            if user:
                return user_id

            # 같은 이메일로 이미 존재하는지 확인 (Google OAuth로 가입한 경우)
            existing = session.query(User).filter_by(email=email).first()
            if existing:
                return str(existing.id)

            # 신규 생성
            session.add(User(
                id=uuid.UUID(user_id),
                google_id=user_id,
                email=email,
                name=email.split("@")[0],
            ))
            return user_id
    except Exception as e:
        logger.warning("사용자 생성 실패: %s", e)
        return user_id


def _set_session_from_supabase(data: dict) -> bool:
    """Supabase auth 응답으로 session_state 세팅. 성공 여부 반환."""
    access_token = data.get("access_token", "")
    if not access_token:
        return False

    refresh_token = data.get("refresh_token", "")
    expires_at    = str(data.get("expires_at", ""))

    payload = _decode_jwt_payload(access_token)
    user_id = payload.get("sub", "")
    email   = payload.get("email", "")

    if not user_id:
        return False

    # 같은 이메일 기존 계정 있으면 그 ID 사용 (Google OAuth ↔ 이메일 연동)
    resolved_id = _ensure_user_exists(user_id, email)
    user_id = resolved_id

    _save_token_to_db(
        user_id, access_token, "",
        supabase_refresh_token=refresh_token,
        expires_at=expires_at,
    )

    st.session_state["user_id"]      = user_id
    st.session_state["email"]        = email
    st.session_state["access_token"] = access_token
    st.session_state["logged_in"]    = True
    st.session_state["token_saved"]  = False  # Gmail 미연동 상태
    st.query_params.clear()
    st.query_params["uid"] = user_id
    return True


def login_with_email(email: str, password: str) -> tuple[bool, str]:
    """이메일/패스워드 로그인. (success, error_msg)"""
    data = _call_supabase_auth("token?grant_type=password", {"email": email, "password": password})
    if "access_token" not in data:
        msg = data.get("error_description") or data.get("msg") or data.get("error") or "로그인 실패"
        return False, str(msg)
    return _set_session_from_supabase(data), ""


def signup_with_email(email: str, password: str) -> tuple[bool, str]:
    """이메일 회원가입. (success, message)"""
    data = _call_supabase_auth("signup", {"email": email, "password": password})
    error_code = data.get("error_code") or data.get("error") or ""
    if error_code == "user_already_exists" or data.get("code") == 422:
        return False, "already_exists"
    if data.get("error") or data.get("error_description"):
        msg = data.get("error_description") or data.get("msg") or data.get("error") or "회원가입 실패"
        return False, str(msg)
    if "access_token" in data:
        _set_session_from_supabase(data)
        return True, "ok"
    return True, "confirm"


def send_password_reset(email: str) -> tuple[bool, str]:
    """비밀번호 재설정 이메일 발송."""
    data = _call_supabase_auth("recover", {"email": email})
    if data.get("error"):
        return False, str(data.get("error"))
    return True, ""


def render_login_page() -> None:
    """로그인 화면 렌더링."""
    st.markdown("""
    <div style="display:flex; flex-direction:column; align-items:center;
                justify-content:center; min-height:30vh; text-align:center;">
        <div style="font-size:48px; margin-bottom:16px;">⚔️</div>
        <h1 style="font-size:32px; margin-bottom:8px;">Slayer AI</h1>
        <p style="color:#888; margin-bottom:24px;">AI-powered Career Command</p>
    </div>
    """, unsafe_allow_html=True)

    col = st.columns([1, 2, 1])[1]
    with col:
        tab_google, tab_email = st.tabs(["Google 로그인", "이메일 로그인"])

        with tab_google:
            oauth_url = get_oauth_url()
            st.markdown(
                f'<a href="{oauth_url}" target="_self" style="'
                "display:block; text-align:center; padding:12px; border-radius:8px;"
                "background:#3b82f6; color:white; text-decoration:none; font-weight:600;"
                "font-size:15px; margin-top:16px;"
                '">Google 계정으로 로그인</a>',
                unsafe_allow_html=True,
            )
            st.caption("Gmail 자동 연동을 위해 Google 로그인을 권장합니다.")

        with tab_email:
            mode = st.radio("", ["로그인", "회원가입", "비밀번호 재설정"], horizontal=True, label_visibility="collapsed")
            email_input = st.text_input("이메일", key="email_input")

            if mode == "로그인":
                password_input = st.text_input("비밀번호", key="pw_input", type="password")
                if st.button("로그인", use_container_width=True, type="primary"):
                    if not email_input or not password_input:
                        st.error("이메일과 비밀번호를 입력해주세요.")
                    else:
                        with st.spinner("로그인 중..."):
                            ok, err = login_with_email(email_input, password_input)
                        if ok:
                            st.rerun()
                        else:
                            st.error(f"로그인 실패: {err}")

            elif mode == "회원가입":
                password_input = st.text_input("비밀번호", key="pw_input2", type="password")
                if st.button("회원가입", use_container_width=True, type="primary"):
                    if not email_input or not password_input:
                        st.error("이메일과 비밀번호를 입력해주세요.")
                    elif len(password_input) < 6:
                        st.error("비밀번호는 6자 이상이어야 합니다.")
                    else:
                        with st.spinner("가입 중..."):
                            ok, msg = signup_with_email(email_input, password_input)
                        if ok and msg == "ok":
                            st.rerun()
                        elif not ok and msg == "already_exists":
                            st.warning("이미 가입된 이메일입니다. '비밀번호 재설정'으로 비밀번호를 설정한 뒤 로그인해주세요.")
                        elif ok and msg == "confirm":
                            st.success("가입 완료! 이메일 확인 후 로그인해주세요.")
                        else:
                            st.error(msg)

            else:  # 비밀번호 재설정
                st.caption("가입된 이메일로 비밀번호 설정 링크를 보내드립니다.")
                if st.button("재설정 이메일 보내기", use_container_width=True, type="primary"):
                    if not email_input:
                        st.error("이메일을 입력해주세요.")
                    else:
                        with st.spinner("전송 중..."):
                            ok, err = send_password_reset(email_input)
                        if ok:
                            st.success(f"{email_input} 으로 비밀번호 설정 링크를 보냈어요. 확인 후 로그인해주세요.")
                        else:
                            st.error(f"전송 실패: {err}")
