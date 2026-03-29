"""JD-Resume Match page."""

import asyncio
import json
import streamlit as st
import plotly.graph_objects as go
from slayer.ui.styles import GLOBAL_CSS
from slayer.ui.components import render_page_header, render_score_donut, render_keyword_tags
from slayer.ui.fixtures import SAMPLE_JD_JSON, SAMPLE_RESUME_JSON


def _run_async(coro):
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None
    if loop and loop.is_running():
        import concurrent.futures
        with concurrent.futures.ThreadPoolExecutor() as pool:
            return pool.submit(asyncio.run, coro).result()
    return asyncio.run(coro)


def render():
    st.html(GLOBAL_CSS)
    render_page_header("JD-Resume Match", "Analyze ATS matching score between job description and resume.")

    if "jd_data" not in st.session_state:
        st.session_state["jd_data"] = SAMPLE_JD_JSON
    if "resume_data" not in st.session_state:
        st.session_state["resume_data"] = SAMPLE_RESUME_JSON

    jd_data = st.session_state["jd_data"]
    resume_data = st.session_state["resume_data"]

    try:
        jd_parsed = json.loads(jd_data)
        resume_parsed = json.loads(resume_data)
        company = jd_parsed.get('company', '?')
        title = jd_parsed.get('title', '?')
        name = resume_parsed.get('personal_info', {}).get('name', '?')
        st.html(f"""
        <div class="sl-card" style="display:flex; justify-content:space-between; align-items:center; padding:16px 20px;">
            <div>
                <span style="font-size:14px; color:#888;">JD</span>
                <span style="font-size:15px; font-weight:600; margin-left:8px;">{company} — {title}</span>
            </div>
            <div>
                <span style="font-size:14px; color:#888;">Candidate</span>
                <span style="font-size:15px; font-weight:600; margin-left:8px;">{name}</span>
            </div>
        </div>
        """)
    except json.JSONDecodeError:
        st.warning("Please check JSON format.")

    run_btn = st.button("📊 Start Matching", type="primary", use_container_width=True)

    if run_btn:
        with st.status("🤖 Analyzing resume match...", expanded=True) as status:
            try:
                from slayer.pipelines.jd_resume_matcher import match_jd_resume
                from slayer.schemas import JDSchema, ParsedResume
                status.write("⏳ 📄 **Parsing JD & Resume**...")
                jd = JDSchema(**json.loads(jd_data))
                resume = ParsedResume(**json.loads(resume_data))
                status.write("✅ 📄 **Parsed** — sending to LLM for ATS analysis")
                status.write("⏳ 🤖 **LLM analyzing** keywords, experience, skills...")
                result = _run_async(match_jd_resume(jd, resume))
                status.write(f"✅ 📊 **Score computed** — ATS {result.ats_score:.0f}/100")
                status.write(f"　　Matched: {len(result.matched_keywords)} keywords | Missing: {len(result.missing_keywords)} keywords")
                status.update(label="✅ Matching complete", state="complete")
                st.session_state["match_result"] = result
                st.session_state["jd_data"] = jd_data
                st.session_state["resume_data"] = resume_data
            except Exception as e:
                status.update(label="❌ Matching failed", state="error")
                st.error(f"Matching failed: {e}")
                return

    if "match_result" not in st.session_state:
        st.info("Click the button above to run matching analysis with sample data.")
        return

    st.divider()
    result = st.session_state["match_result"]
    score = result.ats_score

    col_score, col_report = st.columns([1, 2])
    with col_score:
        render_score_donut(score)
    with col_report:
        st.markdown("### Analysis Report")
        rc1, rc2 = st.columns(2)
        with rc1:
            st.markdown("**KEY STRENGTHS**")
            for s in result.strengths:
                st.markdown(f"✅ {s}")
        with rc2:
            st.markdown("**GAPS IDENTIFIED**")
            for w in result.weaknesses:
                st.markdown(f"⚠️ {w}")

    st.markdown("")
    render_keyword_tags(result.matched_keywords, result.missing_keywords)

    if result.gap_summary:
        st.warning(result.gap_summary)

    if result.score_breakdown:
        st.markdown("#### Score Breakdown")
        categories = list(result.score_breakdown.keys())
        values = list(result.score_breakdown.values())
        colors = [("#28a745" if v >= 20 else "#e67e22" if v >= 10 else "#dc3545") for v in values]
        fig = go.Figure(go.Bar(
            x=values, y=categories, orientation='h',
            marker_color=colors,
            text=[f"{v:.1f}" for v in values],
            textposition='auto',
        ))
        fig.update_layout(
            height=250, margin=dict(l=0, r=0, t=0, b=0),
            plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)',
            font_color='#333',
            xaxis=dict(showgrid=False, zeroline=False),
            yaxis=dict(showgrid=False, autorange='reversed'),
        )
        st.plotly_chart(fig, use_container_width=True)

    with st.expander("📋 Raw JSON"):
        st.json(result.model_dump())

    with st.expander("📂 Source Data"):
        c1, c2 = st.columns(2)
        with c1:
            st.markdown("**Job Description (JD)**")
            new_jd = st.text_area("JD", value=st.session_state["jd_data"], height=200, label_visibility="collapsed", key="match_jd_edit")
        with c2:
            st.markdown("**Resume**")
            new_resume = st.text_area("Resume", value=st.session_state["resume_data"], height=200, label_visibility="collapsed", key="match_resume_edit")
        if st.button("💾 Save Changes", key="save_match_input"):
            st.session_state["jd_data"] = new_jd
            st.session_state["resume_data"] = new_resume
            st.success("Saved. Run matching analysis again to apply.")
            st.rerun()
