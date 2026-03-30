"""Company Research page with real-time agent progress."""

import asyncio
import json
import streamlit as st
from slayer.ui.styles import GLOBAL_CSS
from slayer.ui.components import render_page_header, render_info_card, render_news_list


TOOL_LABELS = {
    "search_news": ("📰", "Searching news"),
    "get_corp_info": ("🏢", "Looking up corporate info"),
    "get_financial_info": ("💰", "Fetching financial data"),
}


def _summarize_tool_result(tool_name: str, raw: str) -> str:
    """Convert raw tool output to human-readable summary."""
    import json as _json
    try:
        data = _json.loads(raw) if isinstance(raw, str) else raw
    except (ValueError, TypeError):
        data = str(raw)

    if tool_name == "search_news":
        if isinstance(data, dict):
            articles = data.get("articles", [])
            if articles:
                titles = [a.get("title", "") for a in articles[:3]]
                return f"{len(articles)} articles found: {', '.join(titles)}"
            return "No articles found"
    elif tool_name == "get_corp_info":
        if isinstance(data, dict) and "corp_name" in data:
            parts = []
            if data.get("corp_name"): parts.append(data["corp_name"])
            if data.get("ceo"): parts.append(f"CEO: {data['ceo']}")
            if data.get("employee_count"): parts.append(f"Employees: {data['employee_count']}")
            if data.get("corp_reg_no"): parts.append(f"crno: {data['corp_reg_no']}")
            return " | ".join(parts)
        if isinstance(data, dict) and not data:
            return "No results found"
    elif tool_name == "get_financial_info":
        if isinstance(data, dict) and data.get("revenue"):
            parts = []
            if data.get("fiscal_year"): parts.append(f"FY{data['fiscal_year']}")
            if data.get("revenue"): parts.append(f"Revenue: {data['revenue']}")
            if data.get("operating_profit"): parts.append(f"Op.Profit: {data['operating_profit']}")
            return " | ".join(parts)
        if isinstance(data, dict) and (not data or data.get("error")):
            return data.get("error", "No data available")

    # Fallback
    s = str(data)
    return s[:100] + "..." if len(s) > 100 else s


def _run_research_with_status(company_name: str, status_container):
    """Run agent with real-time status updates in Streamlit."""
    from slayer.agents.company_research.agent import run_company_research_streaming

    steps = []
    seen_tool_calls = set()  # Prevent duplicate entries

    def on_event(event_type, data):
        if event_type == "thinking":
            status_container.update(label="🤖 Agent is deciding next step...", state="running")

        elif event_type == "tool_call":
            tool = data.get("tool", "unknown")
            tool_input = data.get("input", {})
            # Deduplicate: same tool + same input = skip
            call_key = f"{tool}:{json.dumps(tool_input, sort_keys=True)}"
            if call_key in seen_tool_calls:
                return
            seen_tool_calls.add(call_key)

            icon, label = TOOL_LABELS.get(tool, ("🔧", tool))
            input_parts = []
            if isinstance(tool_input, dict):
                for k, v in tool_input.items():
                    input_parts.append(f"{v}")
            input_display = " → ".join(input_parts) if input_parts else ""

            steps.append({
                "icon": icon, "label": label, "input": input_display,
                "tool": tool, "status": "running", "result": None,
            })
            _render_steps(status_container, steps)

        elif event_type == "tool_result":
            if steps and steps[-1]["status"] == "running":
                tool = steps[-1]["tool"]
                summary = _summarize_tool_result(tool, data.get("summary", ""))
                steps[-1]["status"] = "done"
                steps[-1]["result"] = summary
                _render_steps(status_container, steps)

        elif event_type == "done":
            status_container.update(label="✅ Research complete", state="complete")

    loop = asyncio.new_event_loop()
    try:
        result = loop.run_until_complete(
            run_company_research_streaming(company_name, on_event=on_event)
        )
        # Save to DB (non-blocking)
        try:
            from slayer.db.repository import save_company, save_agent_log
            save_company(result)
            save_agent_log("company_research", "success", input_summary=company_name, output_summary=result.summary[:200] if result.summary else "")
        except Exception:
            pass  # DB failure should not block UI
        return result
    finally:
        loop.close()


def _render_steps(status_container, steps):
    """Render clean progress steps inside st.status."""
    for step in steps:
        icon = step["icon"]
        label = step["label"]
        inp = step.get("input", "")

        if step["status"] == "done":
            status_container.write(f"✅ {icon} **{label}** {inp}")
            if step.get("result"):
                status_container.caption(f"　　{step['result']}")
        else:
            status_container.write(f"⏳ {icon} **{label}** {inp}...")


def render():
    st.html(GLOBAL_CSS)
    render_page_header("Company Research", "Auto-collect and analyze company info, financials, and latest news.")

    col_input, col_btn = st.columns([3, 1])
    with col_input:
        company_name = st.text_input("Company", placeholder="e.g. Kakao, Samsung, Naver", label_visibility="collapsed")
    with col_btn:
        run_btn = st.button("🔍 Start Research", type="primary", use_container_width=True)

    if run_btn and company_name.strip():
        with st.status("🤖 Agent starting...", expanded=True) as status:
            try:
                result = _run_research_with_status(company_name.strip(), status)
                st.session_state["company_research"] = result
            except Exception as e:
                status.update(label="❌ Research failed", state="error")
                st.error(f"Error: {e}")
                return

    if "company_research" not in st.session_state:
        st.html('<div style="text-align:center; padding:60px; color:#666;">Enter a company name and start research.</div>')
        return

    result = st.session_state["company_research"]

    name_en = f" ({result.company_name_en})" if result.company_name_en else ""
    st.markdown(f"### {result.company_name}{name_en}")

    c1, c2 = st.columns(2)
    with c1:
        if result.basic_info:
            bi = result.basic_info
            rows = []
            if bi.industry: rows.append(("Industry", bi.industry))
            if bi.ceo: rows.append(("CEO", bi.ceo))
            if bi.employee_count: rows.append(("Employees", bi.employee_count))
            if bi.headquarters: rows.append(("HQ", bi.headquarters))
            if bi.founded_date: rows.append(("Founded", bi.founded_date))
            if bi.listing_info: rows.append(("Listing", bi.listing_info))
            render_info_card("Basic Info", "🏢", rows)

    with c2:
        if result.financial_info:
            fi = result.financial_info
            rows = []
            if fi.revenue: rows.append(("Revenue", fi.revenue))
            if fi.operating_profit: rows.append(("Op. Profit", fi.operating_profit))
            if fi.net_income: rows.append(("Net Income", fi.net_income))
            if fi.total_assets: rows.append(("Total Assets", fi.total_assets))
            if fi.debt_ratio: rows.append(("Debt Ratio", f"{fi.debt_ratio}%"))
            render_info_card(f"Financials ({fi.fiscal_year or 'N/A'})", "💰", rows)

    if result.summary:
        st.html(f"""
        <div class="sl-card" style="border-left:4px solid #3b82f6;">
            <h4 style="margin:0 0 8px 0; font-size:15px;">📋 Summary</h4>
            <p style="margin:0; font-size:14px; line-height:1.8;">{result.summary}</p>
        </div>
        """)

    if result.recent_news:
        render_news_list(result.recent_news)

    with st.expander("📋 Raw JSON"):
        st.json(result.model_dump())
