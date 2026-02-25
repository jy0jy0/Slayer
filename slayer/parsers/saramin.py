"""Saramin (saramin.co.kr) parser.

Saramin JDs can be plain HTML or embedded in iframes.
Using domcontentloaded to avoid networkidle timeouts.
"""

from __future__ import annotations

from slayer.parser_base import BaseParser, CrawlConfig


class SaraminParser(BaseParser):
    """[개발 중] 사람인(saramin.co.kr) 채용 공고 파서.
    TODO: Gemini LLM 연동을 통한 정형화된 JSON 출력 기능 추가 예정.
    """

    def can_handle(self, url: str) -> bool:
        return "saramin.co.kr" in url

    def get_crawl_config(self) -> CrawlConfig:
        return CrawlConfig(
            wait_until="domcontentloaded",
            js_code=[
                # Wait a bit for dynamic content to render
                "await new Promise(r => setTimeout(r, 2000));",
            ],
            js_wait=3.0,
        )

    def parse(self, raw_html: str, crawl_markdown: str, url: str) -> str:
        soup = self._soup(raw_html)

        sections: list[str] = []

        # ── Title ──
        title = self._select_text(soup, [
            "h1.jv_title",
            ".tit_job",
            "h1",
        ])
        if title:
            sections.append(f"# {title}")

        # ── Company ──
        company = self._select_text(soup, [
            "a.company",
            ".company_name a",
            "a[class*='company']",
        ])
        if company:
            sections.append(f"**회사**: {company}")

        # ── JD detail ──
        detail = self._select_md(soup, [
            ".jv_detail .cont",
            ".jv_cont .cont",
            ".jv_detail",
            ".wrap_jv_cont",
            ".user_content",
        ])
        if detail:
            sections.append(detail)

        # ── Summary ──
        summary = self._select_md(soup, [
            ".jv_summary .cont",
            ".jv_summary",
        ])
        if summary:
            sections.append(summary)

        result = "\n\n".join(sections).strip()

        if len(result) < 100:
            return crawl_markdown

        return result
