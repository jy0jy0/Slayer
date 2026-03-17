"""JobKorea (jobkorea.co.kr) parser — LLM 기반 + 이미지 JD 지원.

담당: 현지

흐름:
1. crawl4ai가 페이지를 렌더링하고 Markdown 생성 (process_iframes=True)
2. Markdown에서 이미지 URL 탐색
3. Gemini에 텍스트 + 이미지를 한 번에 전달 (multimodal) → JDSchema 추출
"""

from __future__ import annotations

import logging
import re

from slayer.pipelines.jd_parser.llm_client import extract_jd, verify_extraction
from slayer.pipelines.jd_parser.parser_base import BaseParser, CrawlConfig, JDLLMError
from slayer.schemas import JDSchema

logger = logging.getLogger(__name__)

_NOISE_IMAGE_PATTERNS = [
    "ads.jobkorea.co.kr",
    "imgs.jobkorea.co.kr",
    "file2.jobkorea.co.kr",
    "ib.adnxs.com",
    "Logo",
    "LogoImage",
    "samsungfire",
    "incruit.com",
    "career",
    "logo",
    "brand",
    "wp-content/uploads",
]


class JobKoreaParser(BaseParser):
    """잡코리아(jobkorea.co.kr) 채용 공고 파서."""

    def can_handle(self, url: str) -> bool:
        return "jobkorea.co.kr" in url

    def get_crawl_config(self) -> CrawlConfig:
        return CrawlConfig(
            js_code=[
                "window.scrollTo(0, document.body.scrollHeight);",
                "await new Promise(r => setTimeout(r, 1000));",
                "window.scrollTo(0, 0);",
            ],
            wait_until="domcontentloaded",
            js_wait=3.0,
            excluded_tags=["nav", "footer", "header", "aside", "script", "style", "noscript"],
            page_timeout=90000,
        )

    def parse(self, raw_html: str, crawl_markdown: str, url: str, **kwargs) -> JDSchema:
        save_raw = kwargs.get("save_raw", False)
        job_title = kwargs.get("job_title")

        if not crawl_markdown or len(str(crawl_markdown).strip()) < 100:
            logger.warning("Markdown이 너무 짧습니다: %d자", len(str(crawl_markdown)))
            return JDSchema(company="", title="", position="", notes=str(crawl_markdown), url=url, platform="jobkorea")

        md_text = crawl_markdown.raw_markdown if hasattr(crawl_markdown, "raw_markdown") else str(crawl_markdown)
        jd_image_urls = self._find_jd_images(crawl_markdown)

        img_save_dir = None
        if save_raw and jd_image_urls:
            from pathlib import Path
            raw_dir = Path(__file__).resolve().parent.parent.parent.parent.parent / "data" / "jds" / "raw"
            id_match = re.search(r"/(\d{4,})", url)
            post_id = id_match.group(1) if id_match else "unknown"
            img_save_dir = str(raw_dir / f"jobkorea_{post_id}_images")

        try:
            if jd_image_urls:
                logger.info("JD 이미지 %d개 → multimodal 추출", len(jd_image_urls))
            else:
                logger.info("LLM으로 JD 추출 중...")

            jd = extract_jd(md_text, image_urls=jd_image_urls or None, save_dir=img_save_dir, job_title=job_title)

            if not jd_image_urls:
                suspicious = verify_extraction(md_text, jd.model_dump())
                if suspicious:
                    logger.warning("Hallucination 의심 %d건: %s", len(suspicious), suspicious[:3])
            else:
                logger.info("이미지 JD 포함: Hallucination 검증 건너뜀")

        except Exception as exc:
            raise JDLLMError(
                f"LLM 추출 실패: {exc}",
                stage="extraction",
                cause=exc,
            ) from exc

        jd.url = url
        jd.platform = "jobkorea"
        return jd

    @staticmethod
    def _find_jd_images(crawl_markdown: str) -> list[str]:
        """Markdown에서 JD 본문 이미지 URL 추출."""
        img_pattern = re.compile(r'!\[.*?\]\((https?://[^\)]+)\)')
        all_urls = img_pattern.findall(str(crawl_markdown))

        jd_images = []
        for url in all_urls:
            url_lower = url.lower()
            if not any(url_lower.endswith(ext) for ext in (".jpg", ".jpeg", ".png", ".gif", ".webp")):
                continue
            if any(noise in url for noise in _NOISE_IMAGE_PATTERNS):
                continue
            jd_images.append(url)

        if jd_images:
            logger.info("JD 이미지 %d개 발견", len(jd_images))

        return jd_images
