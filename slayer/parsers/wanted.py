"""Wanted (wanted.co.kr) parser — LLM 기반 텍스트 JD 추출.

crawl4ai가 생성한 Markdown을 Gemini LLM으로 정제하여
채용 공고 내용을 정형화된 JSON으로 추출합니다.

Wanted는 모든 JD가 텍스트 기반이므로 이미지 처리 없이 텍스트만 추출합니다.
"""

from __future__ import annotations

import logging

from slayer.parser_base import BaseParser, CrawlConfig

logger = logging.getLogger(__name__)


class WantedParser(BaseParser):
    """원티드(wanted.co.kr) 채용 공고 파서."""

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
                # 헤더의 경력/지역 메타 정보를 본문에 삽입 (crawl4ai가 캡처할 수 있도록)
                """
                const infoSpans = document.querySelectorAll('span[class*="JobHeader_JobHeader__Tools__Company__Info"]');
                if (infoSpans.length > 0) {
                    const metaDiv = document.createElement('div');
                    metaDiv.id = 'slayer-meta-info';
                    const parts = [];
                    infoSpans.forEach(span => {
                        const text = span.textContent.trim();
                        if (text && text !== '·') parts.push(text);
                    });
                    metaDiv.textContent = '채용 메타 정보: ' + parts.join(' | ');
                    const article = document.querySelector('section, article, main');
                    if (article) article.prepend(metaDiv);
                }
                """,
                # Wait for the expanded content to render
                "await new Promise(r => setTimeout(r, 2000));",
            ],
            js_wait=3.0,
            wait_until="domcontentloaded",
        )

    def parse(self, raw_html: str, crawl_markdown: str, url: str, **kwargs) -> dict:
        """JD를 정형화된 dict로 반환."""
        job_title = kwargs.get("job_title")

        md_text = crawl_markdown.raw_markdown if hasattr(crawl_markdown, "raw_markdown") else str(crawl_markdown)

        if not md_text or len(md_text.strip()) < 100:
            logger.warning("crawl4ai Markdown이 너무 짧습니다: %d자", len(md_text))
            return {"company": "", "title": "", "notes": md_text}

        try:
            from slayer.llm_client import extract_jd, verify_extraction

            logger.info("LLM으로 JD JSON 추출 중...")
            jd_data = extract_jd(md_text, job_title=job_title)

            # Hallucination 체크 (텍스트 전용이므로 항상 검증)
            suspicious = verify_extraction(md_text, jd_data)
            if suspicious:
                logger.warning(
                    "Hallucination 의심 %d건 발견: %s",
                    len(suspicious),
                    suspicious[:3],
                )
                jd_data["_hallucination_warnings"] = suspicious

        except Exception as exc:
            logger.error("LLM 추출 실패: %s", exc)
            jd_data = {"company": "", "title": "", "notes": md_text}

        # URL과 플랫폼 정보 추가
        jd_data["url"] = url
        jd_data["platform"] = "wanted"

        return jd_data
