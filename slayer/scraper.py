"""Core scraper — crawl4ai wrapper that fetches and parses JDs."""

from __future__ import annotations

import asyncio
import json
import logging
import re
from pathlib import Path

from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig

from slayer.parser_base import CrawlConfig
from slayer.registry import get_parser

logger = logging.getLogger(__name__)

# ── 디렉토리 설정 ─────────────────────────────────────────
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
_RAW_DIR = _PROJECT_ROOT / "raw"
_PARSED_JD_DIR = _PROJECT_ROOT / "parsed_jd"


def _get_filename(url: str) -> str:
    """URL에서 플랫폼_공고ID 형태의 파일명 생성."""
    # 플랫폼 이름 추출 (예: jobkorea, wanted, saramin)
    domain_match = re.search(r"(?:www\.)?([a-z]+)\.", url)
    platform = domain_match.group(1) if domain_match else "unknown"

    # URL에서 마지막 숫자 ID 추출
    id_match = re.search(r"/(\d{4,})", url)
    if id_match:
        post_id = id_match.group(1)
    else:
        import hashlib
        post_id = hashlib.md5(url.encode()).hexdigest()[:10]

    return f"{platform}_{post_id}"


def _save_raw_markdown(url: str, md_text: str) -> None:
    """raw markdown을 raw/ 디렉토리에 저장."""
    _RAW_DIR.mkdir(exist_ok=True)
    filename = _get_filename(url) + "_raw.md"
    filepath = _RAW_DIR / filename
    filepath.write_text(md_text, encoding="utf-8")
    logger.info("Raw markdown 저장: %s (%d자)", filepath.name, len(md_text))


def _save_parsed_jd(url: str, jd_data: dict) -> None:
    """정형화된 JD JSON을 parsed_jd/ 디렉토리에 저장."""
    _PARSED_JD_DIR.mkdir(exist_ok=True)
    filename = _get_filename(url) + ".json"
    filepath = _PARSED_JD_DIR / filename
    filepath.write_text(
        json.dumps(jd_data, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    logger.info("Parsed JD 저장: %s", filepath.name)


def _build_run_config(cfg: CrawlConfig) -> CrawlerRunConfig:
    """Translate our CrawlConfig into a crawl4ai CrawlerRunConfig."""
    kwargs: dict = {
        "process_iframes": True,
        "wait_until": cfg.wait_until,
        "page_timeout": cfg.page_timeout,
        "excluded_tags": cfg.excluded_tags,
        "verbose": False,
    }

    if cfg.css_selector:
        kwargs["css_selector"] = cfg.css_selector

    if cfg.js_code:
        kwargs["js_code"] = cfg.js_code
        kwargs["js_only"] = False

    if cfg.js_wait:
        kwargs["delay_before_return_html"] = cfg.js_wait

    return CrawlerRunConfig(**kwargs)


async def _scrape(url: str, save_raw: bool = False) -> dict:
    """Fetch *url* with crawl4ai and return parsed JD dict."""
    parser = get_parser(url)
    logger.info("Using parser: %s for %s", type(parser).__name__, url)

    crawl_cfg = parser.get_crawl_config()

    browser_cfg = BrowserConfig(
        headless=True,
        verbose=False,
        user_agent_mode="random",
    )
    run_cfg = _build_run_config(crawl_cfg)

    async with AsyncWebCrawler(config=browser_cfg) as crawler:
        result = await crawler.arun(url=url, config=run_cfg)

        if not result.success:
            raise RuntimeError(f"Crawl failed for {url}: {result.error_message}")

        raw_html = result.html or ""
        crawl_md = result.markdown or ""

        # raw markdown 저장 (옵션)
        if save_raw:
            md_text = crawl_md.raw_markdown if hasattr(crawl_md, "raw_markdown") else str(crawl_md)
            _save_raw_markdown(url, md_text)

        # 파싱 (dict 반환)
        parsed = parser.parse(raw_html, crawl_md, url, save_raw=save_raw)

        # parsed_jd/ 에 JSON 저장
        if isinstance(parsed, dict):
            _save_parsed_jd(url, parsed)

        return parsed


def scrape_jd(url: str, save_raw: bool = False) -> dict:
    """Synchronous entry point — scrapes a single JD URL and returns dict."""
    return asyncio.run(_scrape(url, save_raw=save_raw))


async def scrape_jd_async(url: str, save_raw: bool = False) -> dict:
    """Async entry point — scrapes a single JD URL and returns dict."""
    return await _scrape(url, save_raw=save_raw)
