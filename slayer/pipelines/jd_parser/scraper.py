"""웹 스크래핑 + JD 파싱 오케스트레이터.

담당: 현지
"""

from __future__ import annotations

import asyncio
import json
import logging
import re
from pathlib import Path

from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig

from slayer.pipelines.jd_parser.parser_base import CrawlConfig, JDCrawlError
from slayer.pipelines.jd_parser.registry import get_parser
from slayer.schemas import JDSchema

logger = logging.getLogger(__name__)

_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
_RAW_DIR = _PROJECT_ROOT / "data" / "jds" / "raw"
_PARSED_JD_DIR = _PROJECT_ROOT / "data" / "jds"


def _get_filename(url: str) -> str:
    """URL에서 플랫폼_공고ID 형태의 파일명 생성."""
    domain_match = re.search(r"(?:www\.)?([a-z]+)\.", url)
    platform = domain_match.group(1) if domain_match else "unknown"

    id_match = re.search(r"/(\d{4,})", url)
    if id_match:
        post_id = id_match.group(1)
    else:
        import hashlib
        post_id = hashlib.md5(url.encode()).hexdigest()[:10]

    return f"{platform}_{post_id}"


def _save_raw_markdown(url: str, md_text: str) -> None:
    """raw markdown을 data/jds/raw/ 디렉토리에 저장."""
    _RAW_DIR.mkdir(parents=True, exist_ok=True)
    filepath = _RAW_DIR / (_get_filename(url) + "_raw.md")
    filepath.write_text(md_text, encoding="utf-8")
    logger.info("Raw markdown 저장: %s (%d자)", filepath.name, len(md_text))


def _save_parsed_jd(url: str, jd: JDSchema) -> None:
    """정형화된 JD JSON을 data/jds/ 디렉토리에 저장."""
    _PARSED_JD_DIR.mkdir(parents=True, exist_ok=True)
    filepath = _PARSED_JD_DIR / (_get_filename(url) + ".json")
    filepath.write_text(
        json.dumps(jd.model_dump(), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    logger.info("Parsed JD 저장: %s", filepath.name)


def _build_run_config(cfg: CrawlConfig) -> CrawlerRunConfig:
    """CrawlConfig를 crawl4ai CrawlerRunConfig로 변환."""
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


async def _scrape(url: str, save_raw: bool = False, job_title: str | None = None) -> JDSchema:
    """crawl4ai로 URL을 크롤하고 JDSchema를 반환."""
    parser = get_parser(url)
    logger.info("사용 파서: %s (%s)", type(parser).__name__, url)

    browser_cfg = BrowserConfig(headless=True, verbose=False, user_agent_mode="random")
    run_cfg = _build_run_config(parser.get_crawl_config())

    async with AsyncWebCrawler(config=browser_cfg) as crawler:
        result = await crawler.arun(url=url, config=run_cfg)

        if not result.success:
            raise JDCrawlError(f"크롤 실패 ({url}): {result.error_message}")

        raw_html = result.html or ""
        crawl_md = result.markdown or ""

        if save_raw:
            md_text = crawl_md.raw_markdown if hasattr(crawl_md, "raw_markdown") else str(crawl_md)
            _save_raw_markdown(url, md_text)

        result = parser.parse(raw_html, crawl_md, url, save_raw=save_raw, job_title=job_title)
        _save_parsed_jd(url, result.jd)

        return result.jd


def scrape_jd(url: str, save_raw: bool = False, job_title: str | None = None) -> JDSchema:
    """JD URL을 스크래핑하여 JDSchema를 반환 (동기 진입점)."""
    import sys
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
    return asyncio.run(_scrape(url, save_raw=save_raw, job_title=job_title))


async def scrape_jd_async(url: str, save_raw: bool = False, job_title: str | None = None) -> JDSchema:
    """JD URL을 스크래핑하여 JDSchema를 반환 (비동기 진입점)."""
    return await _scrape(url, save_raw=save_raw, job_title=job_title)
