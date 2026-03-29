"""URL → 파서 매핑 레지스트리.

담당: 현지
"""

from __future__ import annotations

from slayer.pipelines.jd_parser.parser_base import BaseParser
from slayer.pipelines.jd_parser.parsers.jobkorea import JobKoreaParser
from slayer.pipelines.jd_parser.parsers.wanted import WantedParser

# 순서 중요: 더 구체적인 패턴을 먼저
_PARSERS: list[BaseParser] = [
    JobKoreaParser(),
    WantedParser(),
]


class _FallbackParser(BaseParser):
    """매칭되는 파서가 없을 때 crawl4ai raw markdown을 그대로 반환."""

    def can_handle(self, url: str) -> bool:
        return True

    def parse(self, raw_html: str, crawl_markdown: str, url: str, **kwargs):
        from slayer.schemas import JDSchema
        md_text = crawl_markdown.raw_markdown if hasattr(crawl_markdown, "raw_markdown") else str(crawl_markdown)
        return JDSchema(company="", title="", position="", notes=md_text, url=url)


_FALLBACK = _FallbackParser()


def get_parser(url: str) -> BaseParser:
    """URL에 맞는 파서를 반환. 없으면 FallbackParser 반환."""
    for parser in _PARSERS:
        if parser.can_handle(url):
            return parser
    return _FALLBACK
