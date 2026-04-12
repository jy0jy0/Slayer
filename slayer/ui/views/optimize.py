"""Resume Optimize page with real-time agent progress."""

import asyncio
import json
import logging
import time
import streamlit as st

logger = logging.getLogger(__name__)
from slayer.ui.events import EventType
from slayer.ui.styles import GLOBAL_CSS
from slayer.ui.components import render_page_header, render_change_list


def _run_optimize_with_status(input_data, status_container):
    """Run optimizer agent with real-time status updates."""
    from slayer.agents.resume_optimizer.agent import optimize_resume_streaming

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
    has_resume = "resume_data" in st.session_state
    has_jd = "jd_data" in st.session_state

    if not has_match:
        st.warning("Run **JD-Resume Match** first. Match results will be auto-loaded.")

    if not has_resume or not has_jd:
        st.warning("Resume and JD data are required. Run **JD-Resume Match** first to load data.")

    st.markdown("#### Optimization Parameters")
    pc1, pc2 = st.columns(2)
    with pc1:
        target_score = st.slider("Target Match Score", 50, 100, 80, 5)
    with pc2:
        max_iter = st.slider("Max Iterations", 1, 5, 3, 1)

    with st.expander("📂 Source Data", expanded=False):
        if has_resume:
            resume_json = st.text_area("Resume JSON", value=st.session_state["resume_data"], height=150)
        else:
            st.warning("No resume data available. Go to **JD-Resume Match** to load resume.")
            resume_json = st.text_area("Resume JSON (manual input)", height=150)
        if has_jd:
            jd_json = st.text_area("JD JSON", value=st.session_state["jd_data"], height=150)
        else:
            st.warning("No JD data available. Go to **JD-Resume Match** to load JD.")
            jd_json = st.text_area("JD JSON (manual input)", height=150)
        if has_match:
            match_json = json.dumps(st.session_state["match_result"].model_dump(), ensure_ascii=False, indent=2)
            st.text_area("Match Result (auto-loaded)", value=match_json, height=100, disabled=True)
        else:
            match_json = st.text_area("Match Result JSON (manual input)", height=100)

    can_run = bool(resume_json) and bool(jd_json) and (has_match or bool(match_json))
    run_btn = st.button("✨ Start Iteration", type="primary", use_container_width=True, disabled=not can_run)

    if run_btn:
        t_start = time.time()
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

                # Update resume_data with optimized version
                if result.optimized_blocks:
                    try:
                        # Convert optimized blocks back to a serializable format
                        optimized_data = resume.model_dump()
                        for block in result.optimized_blocks:
                            bt = block.block_type.value if hasattr(block, 'block_type') else (block.get('block_type') if isinstance(block, dict) else None)
                            content = block.content if hasattr(block, 'content') else (block.get('content') if isinstance(block, dict) else None)
                            if bt and content:
                                # Map block types to resume fields
                                if bt == "summary" and isinstance(content, dict):
                                    optimized_data["summary"] = content.get("text", optimized_data.get("summary"))
                                elif bt == "skills" and isinstance(content, dict):
                                    optimized_data["skills"] = content.get("items", optimized_data.get("skills", []))
                        st.session_state["resume_data"] = json.dumps(optimized_data, ensure_ascii=False, indent=2)
                        st.session_state["resume_source"] = "optimized"
                    except Exception as e:
                        logger.warning("Failed to convert optimized blocks to resume: %s", e)

                # DB save (non-blocking)
                duration_ms = int((time.time() - t_start) * 1000)
                try:
                    from slayer.db.repository import save_agent_log
                    save_agent_log(
                        agent_name="resume_optimizer",
                        status="success",
                        input_summary=f"target={target_score}, max_iter={max_iter}",
                        output_summary=f"final_score={result.final_ats_score:.0f}, improvement={result.score_improvement:+.0f}, iterations={result.iterations_used}",
                        duration_ms=duration_ms,
                    )
                except Exception as e:
                    logger.warning("DB save failed: %s", e)
            except Exception as e:
                status.update(label="❌ Optimization failed", state="error")
                st.error(f"Optimization failed: {e}")
                # DB save failure log (non-blocking)
                try:
                    from slayer.db.repository import save_agent_log
                    save_agent_log(
                        agent_name="resume_optimizer",
                        status="failed",
                        input_summary=f"target={target_score}, max_iter={max_iter}",
                        error_message=str(e)[:500],
                    )
                except Exception as e:
                    logger.warning("DB save failed: %s", e)
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
        pct = (improvement / initial * 100) if initial and initial > 0 else 0
        st.metric("IMPROVEMENT", f"+{pct:.0f}%", f"{result.iterations_used} iterations")

    if result.optimization_summary:
        st.success(result.optimization_summary)

    if result.changes:
        render_change_list(result.changes)

    with st.expander("📋 Raw JSON"):
        st.json(result.model_dump())
