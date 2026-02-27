"""JobKorea (jobkorea.co.kr) parser — LLM 기반 + 이미지 JD 지원.

crawl4ai가 생성한 Markdown을 Gemini LLM으로 정제하여
채용 공고 내용을 정형화된 JSON으로 추출합니다.

흐름:
1. crawl4ai가 페이지를 렌더링하고 Markdown을 생성 (process_iframes=True)
2. Markdown에서 이미지 URL을 탐색
3. Gemini에 텍스트 + 이미지를 한 번에 전달 (multimodal) → JSON 추출
"""

from __future__ import annotations

import logging
import re

from slayer.parser_base import BaseParser, CrawlConfig

logger = logging.getLogger(__name__)

# ── 이미지 URL 필터링 패턴 ──────────────────────────────────

# 노이즈 이미지 (로고, 광고, 트래킹 픽셀 등) — 제외 대상
_NOISE_IMAGE_PATTERNS = [
    "ads.jobkorea.co.kr",
    "imgs.jobkorea.co.kr",
    "file2.jobkorea.co.kr",
    "ib.adnxs.com",
    "Logo",
    "LogoImage",
    "samsungfire",
    "incruit.com",
    # 회사 로고 / 커리어 페이지 이미지
    "career",
    "logo",
    "brand",
    "wp-content/uploads",
]


class JobKoreaParser(BaseParser):
    """Extract JD from JobKorea recruitment pages using LLM."""

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
            excluded_tags=[
                "nav", "footer", "header", "aside", "script", "style",
                "noscript",
            ],
            page_timeout=90000,
        )

    def parse(self, raw_html: str, crawl_markdown: str, url: str, **kwargs) -> dict:
        """JD를 정형화된 dict로 반환."""
        save_raw = kwargs.get("save_raw", False)
        job_title = kwargs.get("job_title")
        if not crawl_markdown or len(crawl_markdown.strip()) < 100:
            logger.warning("crawl4ai Markdown이 너무 짧습니다: %d자", len(crawl_markdown))
            return {"company": "", "title": "", "notes": crawl_markdown}

        md_text = crawl_markdown.raw_markdown if hasattr(crawl_markdown, "raw_markdown") else str(crawl_markdown)

        # ── 이미지 JD 탐색 ──
        jd_image_urls = self._find_jd_images(crawl_markdown)

        # ── 이미지 저장 경로 (--save-raw 시) ──
        img_save_dir = None
        if save_raw and jd_image_urls:
            from pathlib import Path
            raw_dir = Path(__file__).resolve().parent.parent.parent / "raw"
            id_match = re.search(r"/(\d{4,})", url)
            post_id = id_match.group(1) if id_match else "unknown"
            img_save_dir = str(raw_dir / f"jobkorea_{post_id}_images")

        # ── Gemini 1회 호출 (텍스트 + 이미지 multimodal) ──
        try:
            from slayer.llm_client import extract_jd, verify_extraction

            if jd_image_urls:
                logger.info(
                    "JD 이미지 %d개 발견 → 텍스트와 함께 multimodal 추출",
                    len(jd_image_urls),
                )
            else:
                logger.info("LLM으로 JD JSON 추출 중...")

            jd_data = extract_jd(
                md_text,
                image_urls=jd_image_urls or None,
                save_dir=img_save_dir,
                job_title=job_title,
            )

            # Hallucination 체크 (이미지 JD가 없을 때만 진행)
            # 이미지 JD가 포함되면 이미지 속 텍스트가 Markdown 원본에 없어 오탐이 발생하므로 건너뜁니다.
            if not jd_image_urls:
                suspicious = verify_extraction(md_text, jd_data)
                if suspicious:
                    logger.warning(
                        "Hallucination 의심 %d건 발견: %s",
                        len(suspicious),
                        suspicious[:3],
                    )
                    jd_data["_hallucination_warnings"] = suspicious
            else:
                logger.info("이미지 JD 포함됨: Hallucination 사후 검증을 건너뜁니다.")

        except Exception as exc:
            logger.error("LLM 추출 실패: %s", exc)
            jd_data = {"company": "", "title": "", "notes": str(crawl_markdown)}

        # URL과 플랫폼 정보 추가
        jd_data["url"] = url
        jd_data["platform"] = "jobkorea"

        return jd_data

    @staticmethod
    def _find_jd_images(crawl_markdown: str) -> list[str]:
        """Markdown에서 JD 본문 이미지 URL을 찾는다."""
        img_pattern = re.compile(r'!\[.*?\]\((https?://[^\)]+)\)')
        all_urls = img_pattern.findall(crawl_markdown)

        jd_images: list[str] = []
        for url in all_urls:
            url_lower = url.lower()
            if not any(url_lower.endswith(ext) for ext in
                       (".jpg", ".jpeg", ".png", ".gif", ".webp")):
                continue
            if any(noise in url for noise in _NOISE_IMAGE_PATTERNS):
                continue
            jd_images.append(url)

        if jd_images:
            logger.info("JD 이미지 URL %d개 발견: %s", len(jd_images), jd_images)

        return jd_images
