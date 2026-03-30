"""JD-Resume Match page."""

import asyncio
import concurrent.futures
import json
import os
import tempfile
import streamlit as st
import plotly.graph_objects as go
from slayer.ui.styles import GLOBAL_CSS
from slayer.ui.components import render_page_header, render_score_donut, render_keyword_tags


def _run_async(coro):
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None
    if loop and loop.is_running():
        with concurrent.futures.ThreadPoolExecutor() as pool:
            return pool.submit(asyncio.run, coro).result()
    return asyncio.run(coro)


def _scrape_jd_sync(url: str):
    """Scrape JD from URL. Uses ThreadPoolExecutor because scrape_jd calls asyncio.run internally."""
    from slayer.pipelines.jd_parser.scraper import scrape_jd
    with concurrent.futures.ThreadPoolExecutor() as pool:
        return pool.submit(scrape_jd, url, True).result()


def _parse_resume_sync(file_path: str):
    """Parse resume from file path."""
    from slayer.pipelines.resume_parser import parse_resume
    return parse_resume(file_path)


def render():
    st.html(GLOBAL_CSS)
    render_page_header("JD-Resume Match", "Analyze ATS matching score between job description and resume.")

    # ── JD URL Parsing & Resume File Upload ──────────────────────────
    col_jd, col_resume = st.columns(2)

    with col_jd:
        st.markdown("**JD — Parse from URL**")
        jd_url = st.text_input("JD URL", placeholder="https://...", label_visibility="collapsed", key="jd_url_input")
        if st.button("🔗 Parse from URL", key="btn_parse_jd", use_container_width=True, disabled=not jd_url):
            with st.status("Scraping JD from URL...", expanded=True) as status:
                try:
                    status.write("⏳ Fetching page and extracting JD...")
                    jd_schema = _scrape_jd_sync(jd_url)
                    jd_json_str = json.dumps(jd_schema.model_dump(), ensure_ascii=False, indent=2)
                    st.session_state["jd_data"] = jd_json_str
                    st.session_state["jd_source"] = "url"
                    status.write(f"✅ Parsed: **{jd_schema.company}** — {jd_schema.title}")
                    status.update(label="✅ JD parsed from URL", state="complete")
                    st.rerun()
                except Exception as e:
                    status.update(label="❌ JD parsing failed", state="error")
                    st.error(f"Failed to parse JD: {e}")
                    # Clear stale data on failure
                    st.session_state.pop("jd_data", None)
                    st.session_state.pop("jd_source", None)

    with col_resume:
        st.markdown("**Resume — Upload File**")
        uploaded_file = st.file_uploader(
            "Upload Resume", type=["pdf", "docx"], label_visibility="collapsed", key="resume_file_upload"
        )
        if uploaded_file is not None and st.button("📄 Parse Uploaded File", key="btn_parse_resume", use_container_width=True):
            tmp_path = None
            with st.status("Parsing resume file...", expanded=True) as status:
                try:
                    suffix = "." + uploaded_file.name.rsplit(".", 1)[-1]
                    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
                        tmp.write(uploaded_file.getbuffer())
                        tmp_path = tmp.name
                    status.write(f"⏳ Parsing **{uploaded_file.name}**...")
                    resume_schema = _parse_resume_sync(tmp_path)
                    resume_json_str = json.dumps(resume_schema.model_dump(), ensure_ascii=False, indent=2)
                    st.session_state["resume_data"] = resume_json_str
                    st.session_state["resume_source"] = "upload"
                    name = resume_schema.personal_info.name if resume_schema.personal_info else "?"
                    status.write(f"✅ Parsed resume for **{name}**")
                    status.update(label="✅ Resume parsed", state="complete")
                    st.rerun()
                except Exception as e:
                    status.update(label="❌ Resume parsing failed", state="error")
                    st.error(f"Failed to parse resume: {e}")
                    # Clear stale data on failure
                    st.session_state.pop("resume_data", None)
                    st.session_state.pop("resume_source", None)
                finally:
                    if tmp_path and os.path.exists(tmp_path):
                        os.unlink(tmp_path)

    st.markdown("")

    # ── Data Source Indicators ───────────────────────────────────────
    has_jd = "jd_data" in st.session_state
    has_resume = "resume_data" in st.session_state

    ind_c1, ind_c2 = st.columns(2)
    with ind_c1:
        if has_jd:
            source = st.session_state.get("jd_source", "manual")
            st.success(f"✅ JD loaded (source: {source})")
        else:
            st.warning("⚠️ No JD data — enter URL or paste JSON in Source Data below")
    with ind_c2:
        if has_resume:
            source = st.session_state.get("resume_source", "manual")
            st.success(f"✅ Resume loaded (source: {source})")
        else:
            st.warning("⚠️ No Resume data — upload file or paste JSON in Source Data below")

    # ── Summary Card ─────────────────────────────────────────────────
    jd_data = st.session_state.get("jd_data", "")
    resume_data = st.session_state.get("resume_data", "")

    if jd_data and resume_data:
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

    can_match = bool(jd_data) and bool(resume_data)
    run_btn = st.button("📊 Start Matching", type="primary", use_container_width=True, disabled=not can_match)

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

                # DB save (non-blocking)
                try:
                    from slayer.db.repository import save_match_result
                    save_match_result(jd_data, resume_data, result)
                except Exception:
                    pass
            except Exception as e:
                status.update(label="❌ Matching failed", state="error")
                st.error(f"Matching failed: {e}")
                return

    if "match_result" not in st.session_state:
        if can_match:
            st.info("Click the button above to run matching analysis.")
        else:
            st.info("Provide both JD and Resume data, then run matching analysis.")
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
            new_jd = st.text_area("JD", value=st.session_state.get("jd_data", ""), height=200, label_visibility="collapsed", key="match_jd_edit")
        with c2:
            st.markdown("**Resume**")
            new_resume = st.text_area("Resume", value=st.session_state.get("resume_data", ""), height=200, label_visibility="collapsed", key="match_resume_edit")
        if st.button("💾 Save Changes", key="save_match_input"):
            st.session_state["jd_data"] = new_jd
            st.session_state["jd_source"] = "manual"
            st.session_state["resume_data"] = new_resume
            st.session_state["resume_source"] = "manual"
            st.success("Saved. Run matching analysis again to apply.")
            st.rerun()
