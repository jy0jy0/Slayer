"""Wanted (wanted.co.kr) parser — LLM 기반 텍스트 JD 추출.

담당: 현지
"""

from __future__ import annotations

import logging

from slayer.pipelines.jd_parser.llm_client import extract_jd, verify_extraction
from slayer.pipelines.jd_parser.parser_base import BaseParser, CrawlConfig, JDLLMError
from slayer.schemas import JDSchema

logger = logging.getLogger(__name__)


class WantedParser(BaseParser):
    """원티드(wanted.co.kr) 채용 공고 파서."""

    def can_handle(self, url: str) -> bool:
        return "wanted.co.kr" in url

    def get_crawl_config(self) -> CrawlConfig:
        return CrawlConfig(
            js_code=[
                # "상세 정보 더 보기" 버튼 클릭 (네비게이션 "더보기"와 구분)
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
                # 헤더 메타 정보(경력/지역)를 본문에 삽입
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
                "await new Promise(r => setTimeout(r, 2000));",
            ],
            js_wait=3.0,
            wait_until="domcontentloaded",
        )

    def parse(self, raw_html: str, crawl_markdown: str, url: str, **kwargs) -> JDSchema:
        job_title = kwargs.get("job_title")
        md_text = crawl_markdown.raw_markdown if hasattr(crawl_markdown, "raw_markdown") else str(crawl_markdown)

        if not md_text or len(md_text.strip()) < 100:
            logger.warning("Markdown이 너무 짧습니다: %d자", len(md_text))
            return JDSchema(company="", title="", position="", notes=md_text, url=url, platform="wanted")

        try:
            logger.info("LLM으로 JD 추출 중...")
            jd = extract_jd(md_text, job_title=job_title)

            suspicious = verify_extraction(md_text, jd.model_dump())
            if suspicious:
                logger.warning("Hallucination 의심 %d건: %s", len(suspicious), suspicious[:3])

        except Exception as exc:
            raise JDLLMError(
                f"LLM 추출 실패: {exc}",
                stage="extraction",
                cause=exc,
            ) from exc

        jd.url = url
        jd.platform = "wanted"
        return jd
