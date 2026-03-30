"""Slayer Streamlit UI — 멀티페이지 앱 엔트리포인트.

실행:
    cd /Users/jiho-gloz/Desktop/Proj/Slayer
    streamlit run slayer/ui/app.py
"""

import os
import sys
from pathlib import Path

# 프로젝트 루트를 sys.path에 추가 (editable install 없이 동작)
# __file__ 기반 + CWD 기반 모두 시도
_project_root = str(Path(__file__).resolve().parents[2])
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)
_cwd = os.getcwd()
if _cwd not in sys.path:
    sys.path.insert(0, _cwd)

import streamlit as st

st.set_page_config(
    page_title="Slayer AI",
    page_icon="⚔️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# 사이드바 네비게이션
from slayer.ui.views import dashboard, research, matching, optimize, cover_letter, interview_prep

pages = {
    "Dashboard": dashboard,
    "Company Research": research,
    "JD-Resume Match": matching,
    "Resume Optimize": optimize,
    "Cover Letter": cover_letter,
    "Interview Prep": interview_prep,
}

# 사이드바 네비 초기화
if "nav_page" not in st.session_state:
    st.session_state["nav_page"] = "Dashboard"

NAV_ITEMS = [
    ("🏠", "Dashboard"),
    ("🏢", "Company Research"),
    ("📊", "JD-Resume Match"),
    ("✨", "Resume Optimize"),
    ("✍️", "Cover Letter"),
    ("🎯", "Interview Prep"),
]

with st.sidebar:
    st.markdown("### ⚔️ Slayer AI")
    st.caption("CAREER COMMAND")
    st.divider()

    for icon, name in NAV_ITEMS:
        is_active = st.session_state["nav_page"] == name
        btn_type = "primary" if is_active else "secondary"
        if st.button(f"{icon}  {name}", key=f"nav_{name}", use_container_width=True, type=btn_type):
            st.session_state["nav_page"] = name
            st.rerun()

    st.divider()
    st.caption("Status: Ready")

selection = st.session_state["nav_page"]

# 선택된 페이지 렌더링
pages[selection].render()
