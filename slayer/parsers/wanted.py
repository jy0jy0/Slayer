"""Wanted (wanted.co.kr) parser.

Wanted uses a React SPA with a "상세 정보 더 보기" button that must be
clicked to reveal the full job description.
"""

from __future__ import annotations

from slayer.parser_base import BaseParser, CrawlConfig


class WantedParser(BaseParser):
    """[개발 중] 원티드(wanted.co.kr) 채용 공고 파서.
    TODO: Gemini LLM 연동을 통한 정형화된 JSON 출력 기능 추가 예정.
    """

    def can_handle(self, url: str) -> bool:
        return "wanted.co.kr" in url

    def get_crawl_config(self) -> CrawlConfig:
        return CrawlConfig(
            js_code=[
                # Click the "상세 정보 더 보기" button inside the JD article.
                # Must be specific because the nav bar also has a "더보기" button.
                """
                const buttons = document.querySelectorAll('button');
                for (const btn of buttons) {
                    const text = btn.textContent.trim();
                    if (text === '상세 정보 더 보기' || text === '상세 정보 더보기') {
                        btn.scrollIntoView();
                        btn.click();
                        break;
                    }
                }
                """,
                # Wait for the expanded content to render
                "await new Promise(r => setTimeout(r, 2000));",
            ],
            js_wait=3.0,
            wait_until="domcontentloaded",
        )

    def parse(self, raw_html: str, crawl_markdown: str, url: str) -> str:
        soup = self._soup(raw_html)

        sections: list[str] = []

        # ── Title ──
        title = self._select_text(soup, [
            "h1[class*='JobHeader']",
            "h2[class*='JobHeader']",
            "h1[data-testid]",
            "section h1",
            "h1",
        ])
        if title:
            sections.append(f"# {title}")

        # ── Company ──
        company = self._select_text(soup, [
            "a[class*='JobHeader_company']",
            "a[data-attribute-id='company__click']",
            "h5 a",
        ])
        if company:
            sections.append(f"**회사**: {company}")

        # ── JD body — target the article container ──
        detail = self._select_md(soup, [
            "article[class*='JobDescription']",
            "section[class*='JobDescription']",
            "div[class*='JobDescription']",
            "section[class*='JobContent']",
            "div[class*='JobWorkDescription']",
            ".job-description",
        ])
        if detail:
            sections.append(detail)

        result = "\n\n".join(sections).strip()

        # Fallback to crawl4ai markdown if extraction was too thin
        if len(result) < 100:
            return crawl_markdown

        return result
