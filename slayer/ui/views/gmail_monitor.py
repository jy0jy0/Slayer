"""Gmail Monitor 뷰.

로그인된 사용자의 Gmail을 폴링하여 채용 관련 메일을 감지하고
지원 상태 자동 전이 결과를 표시한다.
"""

import streamlit as st
from slayer.ui.styles import GLOBAL_CSS

_STATUS_LABEL = {
    "PASS":      ("✅", "합격/통과"),
    "INTERVIEW": ("📅", "면접 안내"),
    "FAIL":      ("❌", "불합격"),
    "REJECT":    ("🚫", "거절"),
}


def render():
    st.html(GLOBAL_CSS)
    st.markdown("## 📬 Gmail Monitor")
    st.caption("채용 관련 메일을 자동 감지하고 지원 상태를 업데이트합니다.")
    st.divider()

    user_id = st.session_state.get("user_id")
    token_saved = st.session_state.get("token_saved", False)

    # 토큰 미저장 안내
    if not token_saved:
        st.warning("Gmail 연동이 필요합니다. 로그아웃 후 다시 Google 로그인하면 자동으로 연동됩니다.")
        return

    # 폴링 버튼
    col1, col2 = st.columns([2, 1])
    with col1:
        st.markdown("**새 채용 메일 확인**")
        st.caption("마지막 확인 이후 수신된 채용 관련 메일을 분류합니다.")
    with col2:
        run = st.button("📨 메일 확인", use_container_width=True, type="primary")

    if run:
        with st.spinner("Gmail 폴링 중..."):
            try:
                from slayer.pipelines.gmail_monitor.fetcher import poll_user, GmailFetchError
                events = poll_user(user_id)
            except GmailFetchError as e:
                st.error(f"Gmail 폴링 실패 ({e.stage}): {e.cause}")
                return
            except Exception as e:
                st.error(f"오류: {e}")
                return

        st.session_state["gmail_events"] = events

    # 결과 표시
    events = st.session_state.get("gmail_events")
    if events is None:
        st.info("버튼을 눌러 새 메일을 확인하세요.")
        return

    if not events:
        st.success("새로운 채용 관련 메일이 없습니다.")
        return

    st.success(f"{len(events)}건의 채용 메일을 처리했습니다.")
    st.divider()

    for ev in events:
        status_type = ev.get("parsed_status_type", "")
        icon, label = _STATUS_LABEL.get(status_type, ("📧", status_type))
        company = ev.get("parsed_company") or "회사 미상"
        stage   = ev.get("parsed_stage_name") or ""
        subject = ev.get("subject") or ""
        summary = ev.get("raw_summary") or ""

        with st.container():
            st.markdown(f"#### {icon} {company}" + (f" — {stage}" if stage else ""))
            cols = st.columns([1, 3])
            with cols[0]:
                st.markdown(f"**상태** `{label}`")
                if ev.get("received_at"):
                    st.caption(ev["received_at"][:10])
            with cols[1]:
                if subject:
                    st.markdown(f"**제목** {subject}")
                if summary:
                    st.caption(summary)
            st.divider()
