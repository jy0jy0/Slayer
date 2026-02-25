"""Remember Career (career.rememberapp.co.kr) parser."""

from __future__ import annotations

from slayer.parser_base import BaseParser, CrawlConfig


class RememberParser(BaseParser):
    """[개발 중] 리멤버(rememberapp.co.kr) 채용 공고 파서.
    TODO: Gemini LLM 연동을 통한 정형화된 JSON 출력 기능 추가 예정.
    """

    def can_handle(self, url: str) -> bool:
        return "rememberapp.co.kr" in url

    def get_crawl_config(self) -> CrawlConfig:
        return CrawlConfig(
            wait_until="domcontentloaded",
            js_code=[
                "await new Promise(r => setTimeout(r, 2000));",
            ],
            js_wait=3.0,
        )

    def parse(self, raw_html: str, crawl_markdown: str, url: str) -> str:
        soup = self._soup(raw_html)

        sections: list[str] = []

        # ── Title ──
        title = self._select_text(soup, [
            "h1[class*='title']",
            "h1[class*='Title']",
            "h1",
        ])
        if title:
            sections.append(f"# {title}")

        # ── Company ──
        company = self._select_text(soup, [
            "a[class*='company']",
            "span[class*='company']",
            "a[class*='Company']",
        ])
        if company:
            sections.append(f"**회사**: {company}")

        # ── JD content ──
        detail = self._select_md(soup, [
            "div[class*='jobDescription']",
            "div[class*='JobDetail']",
            "div[class*='description']",
            "div[class*='content']",
            "section[class*='detail']",
            "article",
        ])
        if detail:
            sections.append(detail)

        result = "\n\n".join(sections).strip()

        if len(result) < 100:
            return crawl_markdown

        return result
