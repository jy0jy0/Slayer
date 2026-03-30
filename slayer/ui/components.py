"""Slayer UI shared components."""

from __future__ import annotations
import streamlit as st


def render_page_header(title: str, subtitle: str = ""):
    """Page header."""
    st.markdown(f"## {title}")
    if subtitle:
        st.caption(subtitle)
    st.divider()


def render_score_donut(score: float, label: str = "ATS Score"):
    """SVG donut chart for score display."""
    color = "#28a745" if score >= 80 else "#e67e22" if score >= 60 else "#dc3545"
    grade = "Great Match" if score >= 80 else "Moderate" if score >= 60 else "Needs Work"
    pct = score / 100 * 251.2  # circumference = 2*pi*40

    svg = f"""
    <div style="text-align:center; padding:20px;">
        <svg width="160" height="160" viewBox="0 0 100 100">
            <circle cx="50" cy="50" r="40" fill="none" stroke="#e0e0e0" stroke-width="8"/>
            <circle cx="50" cy="50" r="40" fill="none" stroke="{color}" stroke-width="8"
                stroke-dasharray="{pct} 251.2" stroke-dashoffset="0"
                stroke-linecap="round" transform="rotate(-90 50 50)"/>
            <text x="50" y="46" text-anchor="middle" fill="{color}" font-size="22" font-weight="700">{score:.0f}%</text>
            <text x="50" y="58" text-anchor="middle" fill="#888" font-size="7">{label}</text>
        </svg>
        <div style="color:{color}; font-weight:600; font-size:14px; margin-top:4px;">{grade}</div>
    </div>
    """
    st.html(svg)


def render_keyword_tags(matched: list[str], missing: list[str]):
    """Matched/missing keyword tags."""
    html = ""
    if matched:
        html += '<div style="margin-bottom:12px;"><span style="color:#888; font-size:12px; font-weight:600;">MATCHED KEYWORDS</span><br>'
        for kw in matched:
            html += f'<span class="sl-tag-matched">{kw}</span>'
        html += '</div>'
    if missing:
        html += '<div><span style="color:#888; font-size:12px; font-weight:600;">MISSING KEYWORDS</span><br>'
        for kw in missing:
            html += f'<span class="sl-tag-missing">{kw}</span>'
        html += '</div>'
    st.html(html)


def render_info_card(title: str, icon: str, rows: list[tuple[str, str]]):
    """Key-value info card."""
    html = f'<div class="sl-card"><h4 style="margin:0 0 12px 0; font-size:15px;">{icon} {title}</h4>'
    for label, value in rows:
        if value:
            html += f'<div class="sl-info-row"><span class="sl-info-label">{label}</span><span class="sl-info-value">{value}</span></div>'
    html += '</div>'
    st.html(html)


def render_change_list(changes: list):
    """Optimization change list."""
    html = '<div class="sl-card"><h4 style="margin:0 0 12px 0; font-size:15px;">Strategic Changes</h4>'
    for c in changes:
        ct = c.change_type if isinstance(c.change_type, str) else c.change_type
        bt = c.block_type.value if hasattr(c.block_type, 'value') else str(c.block_type)
        html += f'<div style="padding:8px 0; border-bottom:1px solid #2a2a3e; display:flex; align-items:flex-start; gap:8px;">'
        html += f'<span class="sl-badge sl-badge-{ct}">{ct}</span>'
        html += f'<span style="font-size:13px;"><b>{bt}</b>: {c.reason}</span>'
        html += '</div>'
    html += '</div>'
    st.html(html)


def render_news_list(news_items: list):
    """News list."""
    html = '<div class="sl-card"><h4 style="margin:0 0 12px 0; font-size:15px;">📰 Recent News</h4>'
    for n in news_items[:10]:
        title = n.title if hasattr(n, 'title') else n.get('title', '')
        summary = (n.summary if hasattr(n, 'summary') else n.get('summary', '')) or ''
        url = (n.source_url if hasattr(n, 'source_url') else n.get('source_url', '')) or ''
        if url:
            html += f'<div class="sl-news-item"><a href="{url}" target="_blank" style="text-decoration:none;"><div class="sl-news-title" style="color:#3b82f6; cursor:pointer;">{title} ↗</div></a>'
        else:
            html += f'<div class="sl-news-item"><div class="sl-news-title">{title}</div>'
        if summary:
            html += f'<div class="sl-news-summary">{summary}</div>'
        html += '</div>'
    html += '</div>'
    st.html(html)
