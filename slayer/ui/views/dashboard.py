"""Dashboard 뷰 — 지원 현황 + 면접 일정."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

import streamlit as st

from slayer.ui.styles import GLOBAL_CSS

_STATUS_KO = {
    "scrapped":    ("🔖", "스크랩",   "#6b7280"),
    "reviewing":   ("👀", "검토중",   "#3b82f6"),
    "applied":     ("📨", "지원완료", "#8b5cf6"),
    "in_progress": ("⚡", "전형중",   "#f59e0b"),
    "final_pass":  ("🎉", "최종합격", "#10b981"),
    "rejected":    ("❌", "불합격",   "#ef4444"),
    "withdrawn":   ("🚪", "취소",     "#9ca3af"),
}


def _poll_if_needed(user_id: str) -> None:
    """마지막 폴링으로부터 5분 이상 지났으면 Gmail 폴링."""
    now = datetime.now(timezone.utc).timestamp()
    last = st.session_state.get("last_gmail_poll", 0)
    if now - last < 300:
        return

    try:
        from slayer.pipelines.gmail_monitor.fetcher import poll_user
        events = poll_user(user_id)
        st.session_state["last_gmail_poll"] = now
        if events:
            st.session_state["new_mail_count"] = len(events)
    except Exception as e:
        st.session_state["last_gmail_poll"] = now  # 실패해도 타이머 갱신
        st.session_state["poll_error"] = str(e)


def _load_applications(user_id: str) -> list[dict]:
    """applications + company 조인 조회."""
    try:
        from slayer.db.models import Application, Company
        from slayer.db.session import get_session, is_db_available

        if not is_db_available():
            return []

        with get_session() as session:
            rows = (
                session.query(Application, Company.name)
                .join(Company, Application.company_id == Company.id)
                .filter(Application.user_id == uuid.UUID(user_id))
                .order_by(Application.created_at.desc())
                .limit(50)
                .all()
            )
            return [
                {
                    "id": str(app.id),
                    "company": name,
                    "status": app.status,
                    "ats_score": app.ats_score,
                    "applied_at": app.applied_at.strftime("%Y-%m-%d") if app.applied_at else None,
                    "deadline": str(app.deadline) if app.deadline else None,
                }
                for app, name in rows
            ]
    except Exception:
        return []


def _load_gmail_events(user_id: str) -> list[dict]:
    """최근 gmail_events 조회 (최대 20건)."""
    try:
        from slayer.db.models import GmailEvent
        from slayer.db.session import get_session, is_db_available

        if not is_db_available():
            return []

        with get_session() as session:
            rows = (
                session.query(GmailEvent)
                .filter(GmailEvent.user_id == uuid.UUID(user_id))
                .order_by(GmailEvent.received_at.desc())
                .limit(20)
                .all()
            )
            return [
                {
                    "company": e.parsed_company or "?",
                    "status_type": e.parsed_status_type or "",
                    "stage": e.parsed_stage_name or "",
                    "summary": e.raw_summary or "",
                    "received_at": e.received_at.strftime("%m/%d") if e.received_at else "",
                }
                for e in rows
            ]
    except Exception:
        return []


def _load_interviews(user_id: str) -> list[dict]:
    """calendar_events 중 interview 타입 + 미래 일정 조회."""
    try:
        from slayer.db.models import CalendarEvent
        from slayer.db.session import get_session, is_db_available

        if not is_db_available():
            return []

        now = datetime.now(timezone.utc)
        with get_session() as session:
            rows = (
                session.query(CalendarEvent)
                .filter(
                    CalendarEvent.user_id == uuid.UUID(user_id),
                    CalendarEvent.event_type == "interview",
                    CalendarEvent.start_datetime >= now,
                )
                .order_by(CalendarEvent.start_datetime)
                .limit(10)
                .all()
            )
            return [
                {
                    "title": ev.title,
                    "start": ev.start_datetime.strftime("%m/%d %H:%M"),
                    "sync": ev.sync_status,
                }
                for ev in rows
            ]
    except Exception:
        return []


def render():
    st.html(GLOBAL_CSS)
    user_id = st.session_state.get("user_id", "")

    # ── 대시보드 로드 시 자동 Gmail 폴링 ──────────────────
    if user_id and st.session_state.get("token_saved"):
        _poll_if_needed(user_id)

    new_count = st.session_state.pop("new_mail_count", 0)
    poll_error = st.session_state.pop("poll_error", None)

    if new_count:
        st.success(f"📬 새 채용 메일 {new_count}건 처리됨 — 상태가 업데이트됐습니다.")
    if poll_error:
        st.warning(f"Gmail 폴링 오류: {poll_error}")

    # ── 데이터 로드 ───────────────────────────────────────
    apps = _load_applications(user_id) if user_id else []
    interviews = _load_interviews(user_id) if user_id else []
    gmail_events = _load_gmail_events(user_id) if user_id else []

    # ── 요약 카드 ─────────────────────────────────────────
    total      = len(apps)
    in_prog    = sum(1 for a in apps if a["status"] == "in_progress")
    final_pass = sum(1 for a in apps if a["status"] == "final_pass")
    upcoming   = len(interviews)
    mail_count = len(gmail_events)

    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("총 지원", total)
    c2.metric("전형 진행중", in_prog)
    c3.metric("최종 합격", final_pass)
    c4.metric("예정 면접", upcoming)
    c5.metric("감지된 메일", mail_count)

    st.divider()

    col_left, col_right = st.columns([3, 2])

    # ── 지원 현황 ─────────────────────────────────────────
    with col_left:
        st.markdown("#### 지원 현황")
        if not apps:
            st.caption("지원 내역이 없습니다.")
        else:
            for app in apps:
                icon, label, color = _STATUS_KO.get(app["status"], ("•", app["status"], "#888"))
                score = f'  `ATS {app["ats_score"]:.0f}`' if app["ats_score"] else ""
                date  = app["applied_at"] or app["deadline"] or ""
                st.markdown(
                    f'{icon} **{app["company"]}** '
                    f'<span style="color:{color};font-size:12px">{label}</span>'
                    f'{score}  <span style="color:#888;font-size:12px">{date}</span>',
                    unsafe_allow_html=True,
                )

    # ── 면접 일정 ─────────────────────────────────────────
    with col_right:
        st.markdown("#### 예정 면접")
        if not interviews:
            st.caption("예정된 면접이 없습니다.")
        else:
            for iv in interviews:
                sync_icon = "📅" if iv["sync"] == "synced" else "⏳"
                st.markdown(f"{sync_icon} **{iv['title']}**")
                st.caption(iv["start"])
                st.divider()

    # ── 감지된 채용 메일 피드 ─────────────────────────────
    st.divider()
    st.markdown("#### 📬 감지된 채용 메일")

    _STATUS_TYPE_KO = {
        "PASS":      ("✅", "#10b981"),
        "FAIL":      ("❌", "#ef4444"),
        "INTERVIEW": ("📅", "#3b82f6"),
        "REJECT":    ("❌", "#ef4444"),
    }

    if not gmail_events:
        st.caption("감지된 채용 메일이 없습니다. Gmail 연동 후 자동으로 수신됩니다.")
    else:
        for ev in gmail_events:
            icon, color = _STATUS_TYPE_KO.get(ev["status_type"], ("📧", "#888"))
            stage = f" / {ev['stage']}" if ev["stage"] else ""
            st.markdown(
                f'{icon} **{ev["company"]}**'
                f'<span style="color:{color};font-size:12px;margin-left:8px">{ev["status_type"]}{stage}</span>'
                f'<span style="color:#888;font-size:12px;float:right">{ev["received_at"]}</span>',
                unsafe_allow_html=True,
            )
            if ev["summary"]:
                st.caption(ev["summary"])
            st.divider()
