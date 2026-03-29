"""Slayer UI 공용 CSS 스타일 — 라이트/다크 모드 자동 대응."""

GLOBAL_CSS = """
<style>
/* 카드 */
.sl-card {
    border: 1px solid #e0e0e0;
    border-radius: 12px;
    padding: 20px;
    background: #ffffff;
    margin-bottom: 12px;
    box-shadow: 0 1px 3px rgba(0,0,0,0.06);
}
.sl-card:hover {
    border-color: #3b82f6;
    box-shadow: 0 2px 8px rgba(230,126,34,0.12);
}

/* 키워드 태그 */
.sl-tag-matched {
    display: inline-block;
    padding: 4px 12px;
    margin: 3px;
    border-radius: 20px;
    font-size: 12px;
    background: #d4edda;
    color: #155724;
    border: 1px solid #c3e6cb;
}
.sl-tag-missing {
    display: inline-block;
    padding: 4px 12px;
    margin: 3px;
    border-radius: 20px;
    font-size: 12px;
    background: #f8d7da;
    color: #721c24;
    border: 1px solid #f5c6cb;
}

/* 변경 배지 */
.sl-badge {
    display: inline-block;
    padding: 2px 10px;
    border-radius: 4px;
    font-size: 11px;
    font-weight: 600;
    margin-right: 8px;
}
.sl-badge-enhance { background: #cce5ff; color: #004085; }
.sl-badge-reorder { background: #e2d9f3; color: #6f42c1; }
.sl-badge-add_keyword { background: #d4edda; color: #155724; }
.sl-badge-quantify { background: #ffecd2; color: #3b82f6; }
.sl-badge-remove { background: #f8d7da; color: #721c24; }

/* 정보 행 */
.sl-info-row {
    display: flex;
    padding: 8px 0;
    border-bottom: 1px solid #f0f0f0;
    font-size: 14px;
}
.sl-info-label {
    color: #888;
    min-width: 80px;
    flex-shrink: 0;
}
.sl-info-value {
    font-weight: 500;
    color: #333;
}

/* 뉴스 */
.sl-news-item {
    padding: 10px 0;
    border-bottom: 1px solid #f0f0f0;
}
.sl-news-title {
    font-weight: 500;
    color: #333;
    font-size: 14px;
}
.sl-news-summary {
    color: #888;
    font-size: 12px;
    margin-top: 2px;
}

/* 자소서 본문 */
.sl-letter {
    background: #fafafa;
    border: 1px solid #e0e0e0;
    border-left: 4px solid #3b82f6;
    border-radius: 12px;
    padding: 28px;
    line-height: 1.9;
    font-size: 15px;
    color: #333;
}

/* 메트릭 카드 스타일 */
[data-testid="stMetric"] {
    background: #fafafa;
    border: 1px solid #e0e0e0;
    border-radius: 12px;
    padding: 16px;
}

/* 다크 모드 자동 대응 */
@media (prefers-color-scheme: dark) {
    .sl-card { background: #16213e; border-color: #2a2a3e; }
    .sl-card:hover { box-shadow: 0 0 12px rgba(230,126,34,0.15); }
    .sl-info-row { border-color: #2a2a3e; }
    .sl-info-value { color: #e0e0e0; }
    .sl-news-item { border-color: #1a1a2e; }
    .sl-news-title { color: #e0e0e0; }
    .sl-letter { background: #16213e; border-color: #2a2a3e; color: #d0d0d0; }
    .sl-tag-matched { background: rgba(40,167,69,0.2); color: #28a745; border-color: rgba(40,167,69,0.3); }
    .sl-tag-missing { background: rgba(220,53,69,0.2); color: #dc3545; border-color: rgba(220,53,69,0.3); }
    .sl-badge-enhance { background: rgba(0,123,255,0.2); color: #4da3ff; }
    .sl-badge-reorder { background: rgba(111,66,193,0.2); color: #a78bfa; }
    .sl-badge-add_keyword { background: rgba(40,167,69,0.2); color: #28a745; }
    .sl-badge-quantify { background: rgba(230,126,34,0.2); color: #3b82f6; }
    .sl-badge-remove { background: rgba(220,53,69,0.2); color: #dc3545; }
    [data-testid="stMetric"] { background: #16213e; border-color: #2a2a3e; }
}
</style>
"""
