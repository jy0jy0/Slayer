"""Resume Optimize page with real-time agent progress."""

import asyncio
import json
import streamlit as st
from slayer.ui.styles import GLOBAL_CSS
from slayer.ui.components import render_page_header, render_change_list
from slayer.ui.fixtures import SAMPLE_JD_JSON, SAMPLE_RESUME_JSON


def _run_optimize_with_status(input_data, status_container):
    """Run optimizer agent with real-time status updates."""
    from slayer.agents.resume_optimizer.agent import optimize_resume_streaming

    steps = []
    seen = set()

    def on_event(event_type, data):
        if event_type == "thinking":
            status_container.update(label="🤖 Agent deciding next action...", state="running")
        elif event_type == "tool_call":
            tool = data.get("tool", "")
            key = f"call_{tool}_{len(steps)}"
            if key not in seen:
                seen.add(key)
                icon = data.get("icon", "🔧")
                label = data.get("label", tool)
                steps.append({"icon": icon, "label": label, "status": "running", "result": None})
                _render_steps(status_container, steps)
        elif event_type == "tool_result":
            if steps and steps[-1]["status"] == "running":
                steps[-1]["status"] = "done"
                steps[-1]["result"] = data.get("summary", "")
                _render_steps(status_container, steps)
        elif event_type == "done":
            status_container.update(label="✅ Optimization complete", state="complete")

    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(optimize_resume_streaming(input_data, on_event=on_event))
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
    render_page_header("Resume Optimize", "Iteratively optimize resume to reach target ATS score.")

    has_match = "match_result" in st.session_state

    if not has_match:
        st.warning("Run **JD-Resume Match** first. Match results will be auto-loaded.")

    st.markdown("#### Optimization Parameters")
    pc1, pc2 = st.columns(2)
    with pc1:
        target_score = st.slider("Target Match Score", 50, 100, 80, 5)
    with pc2:
        max_iter = st.slider("Max Iterations", 1, 5, 3, 1)

    with st.expander("📂 Source Data", expanded=False):
        resume_json = st.text_area("Resume JSON", value=st.session_state.get("resume_data", SAMPLE_RESUME_JSON), height=150)
        jd_json = st.text_area("JD JSON", value=st.session_state.get("jd_data", SAMPLE_JD_JSON), height=150)
        if has_match:
            match_json = json.dumps(st.session_state["match_result"].model_dump(), ensure_ascii=False, indent=2)
            st.text_area("Match Result (auto-loaded)", value=match_json, height=100, disabled=True)
        else:
            match_json = st.text_area("Match Result JSON (manual input)", height=100)

    run_btn = st.button("✨ Start Iteration", type="primary", use_container_width=True, disabled=not has_match and not match_json)

    if run_btn:
        with st.status("🤖 Starting optimization agent...", expanded=True) as status:
            try:
                from slayer.schemas import JDSchema, MatchResult, ParsedResume, ResumeOptimizationInput

                resume = ParsedResume(**json.loads(resume_json))
                jd = JDSchema(**json.loads(jd_json))
                match_result = st.session_state["match_result"] if has_match else MatchResult(**json.loads(match_json))

                input_data = ResumeOptimizationInput(
                    parsed_resume=resume, jd=jd, match_result=match_result,
                    target_ats_score=float(target_score), max_iterations=max_iter,
                )
                result = _run_optimize_with_status(input_data, status)
                st.session_state["optimization_result"] = result
                st.session_state["optimization_initial_score"] = match_result.ats_score
            except Exception as e:
                status.update(label="❌ Optimization failed", state="error")
                st.error(f"Optimization failed: {e}")
                return

    if "optimization_result" not in st.session_state:
        st.html('<div style="text-align:center; padding:60px; color:#666;">Run matching analysis first, then start optimization.</div>')
        return

    result = st.session_state["optimization_result"]
    initial = st.session_state.get("optimization_initial_score", 0)
    final = result.final_ats_score
    improvement = result.score_improvement

    m1, m2, m3 = st.columns(3)
    with m1:
        st.metric("BEFORE SCORE", f"{initial:.0f} /100")
    with m2:
        st.metric("AFTER SCORE", f"{final:.0f} /100", f"{improvement:+.0f}")
    with m3:
        pct = (improvement / initial * 100) if initial > 0 else 0
        st.metric("IMPROVEMENT", f"+{pct:.0f}%", f"{result.iterations_used} iterations")

    if result.optimization_summary:
        st.success(result.optimization_summary)

    if result.changes:
        render_change_list(result.changes)

    with st.expander("📋 Raw JSON"):
        st.json(result.model_dump())
