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

from slayer.pipelines.jd_parser.llm_client import download_images, extract_jd, identify_roles_in_image, verify_extraction
from slayer.pipelines.jd_parser.parser_base import BaseParser, CrawlConfig, JDLLMError, ParseResult
from slayer.schemas import JDSchema

logger = logging.getLogger(__name__)

_NOISE_IMAGE_PATTERNS = [
    "ads.jobkorea.co.kr",
    "imgs.jobkorea.co.kr",   # 추천공고 회사 로고/썸네일 CDN
    "ib.adnxs.com",
    "samsungfire",
    "incruit.com",
    "logoimage",
    "wp-content/uploads",
    "/logo/",
    "/brand/",
    "co_logo",               # 잡코리아 회사 로고 URL 패턴
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

    def parse(self, raw_html: str, crawl_markdown: str, url: str, **kwargs) -> ParseResult:
        save_raw = kwargs.get("save_raw", False)
        job_title = kwargs.get("job_title")

        if not crawl_markdown or len(str(crawl_markdown).strip()) < 100:
            logger.warning("Markdown이 너무 짧습니다: %d자", len(str(crawl_markdown)))
            return ParseResult(jd=JDSchema(company="", title="", position="", notes=str(crawl_markdown), url=url, platform="jobkorea"))

        md_text = crawl_markdown.raw_markdown if hasattr(crawl_markdown, "raw_markdown") else str(crawl_markdown)

        if job_title:
            from slayer.pipelines.jd_parser.section_extractor import extract_role_section
            md_text = extract_role_section(md_text, job_title)

        jd_image_urls = self._find_jd_images(raw_html, md_text)

        img_save_dir = None
        if save_raw and jd_image_urls:
            from pathlib import Path
            raw_dir = Path(__file__).resolve().parent.parent.parent.parent.parent / "data" / "jds" / "raw"
            id_match = re.search(r"/(\d{4,})", url)
            post_id = id_match.group(1) if id_match else "unknown"
            img_save_dir = str(raw_dir / f"jobkorea_{post_id}_images")

        try:
            suspicious: list[str] = []

            if jd_image_urls and job_title:
                # 2-pass: 1차로 직무 목록 파악 → 2차에서 다른 직무 명시적 배제
                # 이미지를 한 번만 다운로드하여 두 호출에 재사용
                logger.info("JD 이미지 %d개 다운로드 중...", len(jd_image_urls))
                image_data = download_images(jd_image_urls, save_dir=img_save_dir)

                logger.info("JD 이미지 %d개 + job_title → 2-pass 추출", len(image_data))
                all_roles = identify_roles_in_image(image_data)
                other_roles = [r for r in all_roles if r.lower() != job_title.lower()] or None
                if other_roles:
                    logger.info("다른 직무 감지 → 명시적 배제: %s", other_roles)

                # 두 번의 이미지 Gemini 호출 사이에 딜레이를 둬서 연속 요청으로 인한 503 방지
                import time as _time
                logger.info("2차 LLM 호출 전 3초 대기...")
                _time.sleep(3)

                jd = extract_jd(
                    md_text, image_data=image_data,
                    job_title=job_title, other_roles=other_roles,
                )

            elif jd_image_urls:
                logger.info("JD 이미지 %d개 → multimodal 추출", len(jd_image_urls))
                jd = extract_jd(md_text, image_urls=jd_image_urls, save_dir=img_save_dir, job_title=job_title)

            else:
                logger.info("LLM으로 JD 추출 중...")
                jd = extract_jd(md_text, image_urls=None, save_dir=None, job_title=job_title)
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
        jd.platform = "jobkorea"
        return ParseResult(jd=jd, suspicious_items=suspicious, image_urls=jd_image_urls)

    @staticmethod
    def _find_jd_images(raw_html: str, crawl_markdown: str) -> list[str]:
        """JD 본문 이미지 URL 추출.

        1차: crawl4ai 마크다운의 ![](url) 패턴 — 도메인 무관하게 본문 이미지를 잡음.
        2차: HTML <img> 태그 파싱 (fallback) — crawl4ai가 마크다운에 담지 못한 경우 보완.
        """
        import re
        from bs4 import BeautifulSoup

        seen: set[str] = set()
        deduped: list[str] = []

        # 1차: 마크다운에서 추출 (primary)
        for url in re.findall(r'!\[.*?\]\((https?://[^)]+)\)', crawl_markdown):
            if url in seen:
                continue
            if any(noise in url.lower() for noise in _NOISE_IMAGE_PATTERNS):
                continue
            seen.add(url)
            deduped.append(url)

        if deduped:
            logger.info("마크다운 이미지 %d개 선별", len(deduped))
            return deduped

        # 2차: HTML <img> 태그 파싱 (fallback — JS lazy-load 등 마크다운 누락 대비)
        _JD_IMAGE_DOMAINS = [
            "file2.jobkorea.co.kr",
            "file.jobkorea.co.kr",
        ]
        soup = BeautifulSoup(raw_html, "html.parser")
        for tag in soup.find_all("img"):
            src = (
                tag.get("data-src")
                or tag.get("data-original")
                or tag.get("src")
                or ""
            )
            if src.startswith("//"):
                src = "https:" + src
            if not src.startswith("http") or src in seen:
                continue
            if not any(domain in src for domain in _JD_IMAGE_DOMAINS):
                continue
            if any(noise in src.lower() for noise in _NOISE_IMAGE_PATTERNS):
                continue
            seen.add(src)
            deduped.append(src)

        logger.info("HTML 이미지 %d개 선별 (fallback)", len(deduped))
        return deduped
