"""플랫폼별 파서 베이스 클래스 및 예외 정의.

담당: 현지
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field

from slayer.schemas import JDSchema


# ── 예외 계층 ─────────────────────────────────────────────


class JDParseError(Exception):
    """JD 파싱 파이프라인 베이스 예외."""


class JDCrawlError(JDParseError):
    """웹 크롤링 실패 (네트워크 오류, 렌더링 실패 등)."""


class JDLLMError(JDParseError):
    """LLM 추출 실패 (API 오류, 응답 파싱 오류 등).

    Attributes:
        stage: 실패 단계 ("extraction" | "validation")
        cause: 원본 예외
    """

    def __init__(self, message: str, stage: str, cause: Exception) -> None:
        super().__init__(message)
        self.stage = stage
        self.cause = cause


@dataclass
class CrawlConfig:
    """Per-platform crawl configuration hints."""

    js_code: list[str] = field(default_factory=list)
    js_wait: float = 2.0
    css_selector: str | None = None
    excluded_tags: list[str] = field(
        default_factory=lambda: ["nav", "footer", "header", "aside", "script", "style", "noscript"],
    )
    wait_until: str = "domcontentloaded"
    page_timeout: int = 60000


@dataclass
class ParseResult:
    """파서 반환값 컨테이너."""
    jd: JDSchema
    suspicious_items: list[str] = field(default_factory=list)
    image_urls: list[str] = field(default_factory=list)


class BaseParser(ABC):
    """플랫폼별 JD 파서 추상 베이스 클래스."""

    @abstractmethod
    def can_handle(self, url: str) -> bool:
        """이 파서가 해당 URL을 처리할 수 있으면 True 반환."""
        ...

    def get_crawl_config(self) -> CrawlConfig:
        """플랫폼별 크롤 설정 반환. 서브클래스에서 오버라이드 가능."""
        return CrawlConfig()

    @abstractmethod
    def parse(self, raw_html: str, crawl_markdown: str, url: str, **kwargs) -> ParseResult:
        """크롤된 페이지에서 JD를 추출하여 (JDSchema, suspicious_items) 튜플로 반환.

        Args:
            raw_html: 렌더링된 전체 HTML.
            crawl_markdown: crawl4ai가 생성한 Markdown.
            url: 스크래핑한 원본 URL.

        Returns:
            (JDSchema, suspicious_items) — suspicious_items는 hallucination 의심 텍스트 목록.
            이미지 기반 추출이면 suspicious_items는 빈 리스트.
        """
        ...

    # ── HTML 파싱 헬퍼 ────────────────────────────────────

    def _soup(self, raw_html: str):
        """BeautifulSoup 객체 반환."""
        from bs4 import BeautifulSoup
        return BeautifulSoup(raw_html, "html.parser")

    def _select_text(self, soup, selectors: list[str]) -> str:
        """셀렉터 목록을 순서대로 시도하여 첫 번째 매칭 텍스트 반환."""
        for sel in selectors:
            el = soup.select_one(sel)
            if el:
                return el.get_text(strip=True)
        return ""

    def _select_md(self, soup, selectors: list[str]) -> str:
        """셀렉터 목록을 순서대로 시도하여 첫 번째 매칭 요소의 텍스트 반환."""
        for sel in selectors:
            el = soup.select_one(sel)
            if el:
                return el.get_text(separator="\n", strip=True)
        return ""
