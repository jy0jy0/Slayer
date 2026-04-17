"""Dashboard page."""

import streamlit as st
from slayer.ui.styles import GLOBAL_CSS


def render():
    st.html(GLOBAL_CSS)

    st.markdown("## Slayer AI")
    st.caption("Career Command — AI-powered Job Preparation Agent")
    st.divider()

    cols = st.columns(3)

    cards = [
        ("🏢", "Company Research", "Auto-collect and analyze company info, financials, and latest news."),
        ("📄", "JD Parser", "Parse job descriptions from JobKorea or Wanted URLs into structured data."),
        ("📊", "JD-Resume Match", "Analyze ATS matching score between job description and resume."),
    ]

    for col, (icon, title, desc) in zip(cols, cards):
        with col:
            st.html(f"""
            <div class="sl-card" style="text-align:center; min-height:160px; display:flex; flex-direction:column; justify-content:center;">
                <div style="font-size:32px; margin-bottom:8px;">{icon}</div>
                <h3 style="margin:0 0 6px 0; font-size:16px; color:inherit;">{title}</h3>
                <p style="color:#888; font-size:13px; margin:0; line-height:1.5;">{desc}</p>
            </div>
            """)

    row2 = st.columns(3)
    row2_cards = [
        ("✨", "Resume Optimize", "Iteratively optimize resume to reach target ATS score."),
        ("✍️", "Cover Letter", "Generate tailored cover letters based on JD, resume, and company research."),
        ("🎯", "Interview Prep", "Generate tailored interview questions by category."),
    ]

    for col, (icon, title, desc) in zip(row2, row2_cards):
        with col:
            st.html(f"""
            <div class="sl-card" style="text-align:center; min-height:140px; display:flex; flex-direction:column; justify-content:center;">
                <div style="font-size:32px; margin-bottom:8px;">{icon}</div>
                <h3 style="margin:0 0 6px 0; font-size:16px; color:inherit;">{title}</h3>
                <p style="color:#888; font-size:13px; margin:0; line-height:1.5;">{desc}</p>
            </div>
            """)

    st.html("""
    <div class="sl-card" style="padding:20px; margin-top:8px;">
        <h3 style="margin:0 0 12px 0; font-size:16px; color:#888;">Quick Start</h3>
        <div style="color:#b0b0b0; font-size:13px; line-height:2;">
            <b style="color:#3b82f6;">1.</b> Company Research → Analyze target company<br>
            <b style="color:#3b82f6;">2.</b> JD Parser → Parse job description from URL<br>
            <b style="color:#3b82f6;">3.</b> JD-Resume Match → Check ATS score<br>
            <b style="color:#3b82f6;">4.</b> Resume Optimize → Improve score<br>
            <b style="color:#3b82f6;">5.</b> Cover Letter → Generate tailored letter<br>
            <b style="color:#3b82f6;">6.</b> Interview Prep → Prepare for interviews
        </div>
    </div>
    """)

    st.markdown("")
    st.caption("👈 Select a feature from the sidebar. Results auto-forward to the next step.")
