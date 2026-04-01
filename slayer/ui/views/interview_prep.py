"""Interview Prep page — generate tailored interview questions by category."""

import json
import logging
import time
import streamlit as st

logger = logging.getLogger(__name__)
from slayer.ui.styles import GLOBAL_CSS
from slayer.ui.components import render_page_header


# Category display config: (label, emoji)
_CATEGORY_DISPLAY = {
    "기술": ("Technical", "💻"),
    "경험": ("Experience", "📋"),
    "상황/행동": ("Situational / Behavioral", "🎭"),
    "인성": ("Personality", "🧠"),
    "컬처핏": ("Culture Fit", "🤝"),
    "기업 이해도": ("Company Knowledge", "🏢"),
}


def render():
    st.html(GLOBAL_CSS)
    render_page_header("Interview Prep", "Generate tailored interview questions based on JD and resume.")

    # ── Prerequisites ────────────────────────────────────────────────
    has_jd = "jd_data" in st.session_state
    has_resume = "resume_data" in st.session_state
    has_research = "company_research" in st.session_state
    has_match = "match_result" in st.session_state

    cols = st.columns(4)
    with cols[0]:
        st.success("JD loaded") if has_jd else st.warning("JD not loaded")
    with cols[1]:
        st.success("Resume loaded") if has_resume else st.warning("Resume not loaded")
    with cols[2]:
        if has_research:
            st.success(f"Research: {st.session_state['company_research'].company_name}")
        else:
            st.info("No research (optional)")
    with cols[3]:
        if has_match:
            st.success(f"Match: ATS {st.session_state['match_result'].ats_score:.0f}")
        else:
            st.info("No match (optional)")

    if not has_jd or not has_resume:
        st.warning("JD and Resume are required. Please run JD-Resume Match first or provide data.")
        return

    # ── Config ───────────────────────────────────────────────────────
    questions_per_category = st.slider(
        "Questions per category", min_value=1, max_value=10, value=3, key="interview_qpc"
    )

    # ── Generate ─────────────────────────────────────────────────────
    run_btn = st.button("🎯 Generate Interview Questions", type="primary", use_container_width=True)

    if run_btn:
        t_start = time.time()
        with st.status("Generating interview questions...", expanded=True) as status:
            try:
                from slayer.pipelines.interview_questions import generate_interview_questions
                from slayer.schemas import (
                    InterviewQuestionsInput, JDSchema, ParsedResume,
                    CompanyResearchOutput, MatchResult,
                )

                status.write("⏳ Preparing input data...")
                jd = JDSchema(**json.loads(st.session_state["jd_data"]))
                resume = ParsedResume(**json.loads(st.session_state["resume_data"]))
                cr = st.session_state.get("company_research")
                mr = st.session_state.get("match_result")

                inp = InterviewQuestionsInput(
                    jd=jd,
                    resume=resume,
                    company_research=cr,
                    match_result=mr,
                    questions_per_category=questions_per_category,
                )

                status.write("⏳ Calling LLM to generate questions...")
                result = generate_interview_questions(inp)
                st.session_state["interview_result"] = result

                status.write(f"✅ Generated **{len(result.questions)}** questions across categories")
                if result.excluded_categories:
                    status.write(f"ℹ️ Excluded categories (insufficient data): {', '.join(result.excluded_categories)}")
                status.update(label="✅ Interview questions generated", state="complete")

                # DB save (non-blocking)
                duration_ms = int((time.time() - t_start) * 1000)
                try:
                    from slayer.db.repository import save_agent_log
                    save_agent_log(
                        agent_name="interview_prep",
                        status="success",
                        input_summary=f"questions_per_category={questions_per_category}, company={jd.company}, title={jd.title}",
                        output_summary=f"total_questions={len(result.questions)}, excluded={result.excluded_categories or []}, weak_areas={len(result.weak_areas) if result.weak_areas else 0}",
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
                        agent_name="interview_prep",
                        status="failed",
                        error_message=str(e)[:500],
                    )
                except Exception as e:
                    logger.warning("DB save failed: %s", e)
                return

    if "interview_result" not in st.session_state:
        st.info("Click the button above to generate interview questions.")
        return

    st.divider()
    result = st.session_state["interview_result"]

    # ── Excluded categories notice ───────────────────────────────────
    if result.excluded_categories:
        st.warning(
            f"Excluded categories due to missing data: **{', '.join(result.excluded_categories)}**. "
            "Provide Company Research and Match Result to enable all categories."
        )

    # ── Questions by category ────────────────────────────────────────
    st.markdown("### Questions by Category")

    # Group questions by category
    by_category: dict[str, list] = {}
    for q in result.questions:
        cat = q.category.value if hasattr(q.category, "value") else str(q.category)
        by_category.setdefault(cat, []).append(q)

    for cat, questions in by_category.items():
        display_label, emoji = _CATEGORY_DISPLAY.get(cat, (cat, "❓"))
        with st.expander(f"{emoji} {display_label} ({cat}) — {len(questions)} questions", expanded=True):
            for i, q in enumerate(questions, 1):
                st.markdown(f"**Q{i}. {q.question}**")
                st.caption(f"Intent: {q.intent}")
                st.html(
                    f'<div style="background:#1a2744; border-left:3px solid #3b82f6; '
                    f'padding:8px 12px; margin:4px 0 12px 0; border-radius:4px; '
                    f'font-size:13px; color:#93b5e8;">💡 Tip: {q.tip}</div>'
                )
                source_label = q.source
                st.html(
                    f'<span style="display:inline-block; background:#2a2a3e; color:#888; '
                    f'padding:2px 8px; border-radius:4px; font-size:11px; margin-bottom:16px;">'
                    f'Source: {source_label}</span>'
                )

    # ── Sample Answers ───────────────────────────────────────────────
    if result.sample_answers:
        st.markdown("### Sample Answers")
        for sa in result.sample_answers:
            with st.expander(f"💬 {sa.question}"):
                st.markdown(sa.answer)

    # ── Weak Areas / Priority ────────────────────────────────────────
    if result.weak_areas:
        st.markdown("### Priority Areas")
        st.caption("Areas to focus your preparation on.")
        for area in result.weak_areas:
            st.markdown(f"- ⚠️ {area}")

    # ── Raw JSON ─────────────────────────────────────────────────────
    with st.expander("📋 Raw JSON"):
        st.json(result.model_dump())
