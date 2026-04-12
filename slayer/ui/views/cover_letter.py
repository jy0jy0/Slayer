"""Cover Letter page with real-time agent progress."""

import asyncio
import json
import logging
import time
import streamlit as st

logger = logging.getLogger(__name__)
from slayer.ui.events import EventType
from slayer.ui.styles import GLOBAL_CSS
from slayer.ui.components import render_page_header, render_score_donut


def _run_cover_letter_with_status(input_data, status_container):
    """Run cover letter agent with real-time status updates."""
    from slayer.agents.cover_letter.agent import generate_cover_letter_streaming

    steps = []
    seen = set()

    def on_event(event_type, data):
        if event_type == EventType.THINKING:
            status_container.update(label="🤖 Agent deciding next action...", state="running")
        elif event_type == EventType.TOOL_CALL:
            tool = data.get("tool", "")
            key = f"call_{tool}_{len(steps)}"
            if key not in seen:
                seen.add(key)
                icon = data.get("icon", "🔧")
                label = data.get("label", tool)
                steps.append({"icon": icon, "label": label, "status": "running", "result": None})
                _render_steps(status_container, steps)
        elif event_type == EventType.TOOL_RESULT:
            if steps and steps[-1]["status"] == "running":
                steps[-1]["status"] = "done"
                steps[-1]["result"] = data.get("summary", "")
                _render_steps(status_container, steps)
        elif event_type == EventType.DONE:
            status_container.update(label="✅ Cover letter complete", state="complete")

    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(generate_cover_letter_streaming(input_data, on_event=on_event))
    finally:
        loop.close()


def _render_steps(status_container, steps):
    for step in steps:
        icon = step["icon"]
        label = step["label"]
        if step["status"] == "done":
            status_container.write(f"✅ {icon} **{label}**")
            if step.get("result"):
                status_container.caption(f"　　{step['result']}")
        else:
            status_container.write(f"⏳ {icon} **{label}**...")


def render():
    st.html(GLOBAL_CSS)
    render_page_header("Cover Letter Engine", "Generate tailored cover letters based on JD, resume, and company research.")

    has_research = "company_research" in st.session_state
    has_match = "match_result" in st.session_state
    has_resume = "resume_data" in st.session_state
    has_jd = "jd_data" in st.session_state

    # ── Data Source Indicators ───────────────────────────────────────
    status_cols = st.columns(4)
    with status_cols[0]:
        if has_jd:
            source = st.session_state.get("jd_source", "manual")
            st.success(f"✅ JD loaded ({source})")
        else:
            st.warning("⚠️ No JD data")
    with status_cols[1]:
        if has_resume:
            source = st.session_state.get("resume_source", "manual")
            st.success(f"✅ Resume loaded ({source})")
        else:
            st.warning("⚠️ No Resume data")
    with status_cols[2]:
        if has_research:
            st.success(f"✅ Research: {st.session_state['company_research'].company_name}")
        else:
            st.warning("Company research not found — run Company Research first.")
    with status_cols[3]:
        if has_match:
            st.success(f"✅ Match: ATS {st.session_state['match_result'].ats_score:.0f}")
        else:
            st.warning("Match result not found — run JD-Resume Match first.")

    with st.expander("📂 Source Data", expanded=False):
        if has_resume:
            resume_json = st.text_area("Resume JSON", value=st.session_state["resume_data"], height=150)
        else:
            st.warning("No resume data. Go to **JD-Resume Match** to load resume.")
            resume_json = st.text_area("Resume JSON (manual input)", height=150)
        if has_jd:
            jd_json = st.text_area("JD JSON", value=st.session_state["jd_data"], height=150)
        else:
            st.warning("No JD data. Go to **JD-Resume Match** to load JD.")
            jd_json = st.text_area("JD JSON (manual input)", height=150)
        if has_research:
            company_json = json.dumps(st.session_state["company_research"].model_dump(), ensure_ascii=False, indent=2)
        else:
            company_json = st.text_area("Company Research JSON (manual input)", height=100)
        if has_match:
            match_json = json.dumps(st.session_state["match_result"].model_dump(), ensure_ascii=False, indent=2)
        else:
            match_json = st.text_area("Match Result JSON (manual input)", height=100)

    can_run = bool(resume_json) and bool(jd_json) and (has_research or bool(company_json)) and (has_match or bool(match_json))
    run_btn = st.button("✍️ Generate Cover Letter", type="primary", use_container_width=True, disabled=not can_run)

    if run_btn:
        t_start = time.time()
        with st.status("🤖 Starting cover letter agent...", expanded=True) as status:
            try:
                from slayer.schemas import CoverLetterInput, CompanyResearchOutput, JDSchema, MatchResult, ParsedResume

                resume = ParsedResume(**json.loads(resume_json))
                jd = JDSchema(**json.loads(jd_json))
                company = st.session_state["company_research"] if has_research else CompanyResearchOutput(**json.loads(company_json))
                match_result = st.session_state["match_result"] if has_match else MatchResult(**json.loads(match_json))

                input_data = CoverLetterInput(parsed_resume=resume, jd=jd, company_research=company, match_result=match_result)
                result = _run_cover_letter_with_status(input_data, status)
                st.session_state["cover_letter_result"] = result

                # DB save (non-blocking)
                duration_ms = int((time.time() - t_start) * 1000)
                try:
                    from slayer.db.repository import save_agent_log
                    save_agent_log(
                        agent_name="cover_letter",
                        status="success",
                        input_summary=f"jd={jd.company}/{jd.title}, resume={resume.personal_info.name if resume.personal_info else '?'}",
                        output_summary=f"words={result.word_count}, coverage={result.jd_keyword_coverage:.2f}, key_points={len(result.key_points) if result.key_points else 0}",
                        duration_ms=duration_ms,
                    )
                except Exception as e:
                    logger.warning("DB save failed: %s", e)
            except Exception as e:
                status.update(label="❌ Generation failed", state="error")
                st.error(f"Generation failed: {e}")
                # DB save failure log (non-blocking)
                try:
                    from slayer.db.repository import save_agent_log
                    save_agent_log(
                        agent_name="cover_letter",
                        status="failed",
                        error_message=str(e)[:500],
                    )
                except Exception as e:
                    logger.warning("DB save failed: %s", e)
                return

    if "cover_letter_result" not in st.session_state:
        st.html('<div style="text-align:center; padding:60px; color:#666;">Complete all inputs and generate your cover letter.</div>')
        return

    result = st.session_state["cover_letter_result"]
    st.markdown("### Letter Drafted.")
    st.caption("Based on your resume and the target role.")

    mc1, mc2, mc3 = st.columns(3)
    with mc1:
        cov_pct = result.jd_keyword_coverage * 100
        render_score_donut(cov_pct, "Keyword Coverage")
    with mc2:
        st.html(f"""
        <div style="text-align:center; padding:24px;">
            <div style="color:#888; font-size:12px; margin-bottom:4px;">VOLUME</div>
            <div style="font-size:36px; font-weight:700;">{result.word_count}</div>
            <div style="color:#888; font-size:12px;">Characters</div>
        </div>
        """)
    with mc3:
        if result.key_points:
            st.html(f"""
            <div style="text-align:center; padding:24px;">
                <div style="color:#888; font-size:12px; margin-bottom:4px;">KEY POINTS</div>
                <div style="font-size:36px; font-weight:700;">{len(result.key_points)}</div>
                <div style="color:#888; font-size:12px;">Strategic Points</div>
            </div>
            """)

    if result.key_points:
        st.html('<div class="sl-card"><h4 style="margin:0 0 8px 0; font-size:14px; color:#3b82f6;">STRATEGIC KEY POINTS</h4>')
        points_html = ""
        for p in result.key_points:
            points_html += f'<div style="padding:4px 0; font-size:13px;">✅ {p}</div>'
        st.html(f'{points_html}</div>')

    letter_html = result.cover_letter.replace("\n\n", "<br><br>").replace("\n", "<br>")
    st.html(f'<div class="sl-letter">{letter_html}</div>')

    with st.expander("📋 Raw JSON"):
        st.json(result.model_dump())
