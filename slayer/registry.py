"""Parser registry — maps URLs to the appropriate platform parser."""

from __future__ import annotations

from slayer.parser_base import BaseParser
from slayer.parsers.jobkorea import JobKoreaParser
from slayer.parsers.saramin import SaraminParser
from slayer.parsers.wanted import WantedParser
from slayer.parsers.remember import RememberParser

# Order matters: more specific patterns first.
_PARSERS: list[BaseParser] = [
    JobKoreaParser(),
    SaraminParser(),
    WantedParser(),
    RememberParser(),
]


class _FallbackParser(BaseParser):
    """Returns crawl4ai raw markdown when no specific parser matches."""

    def can_handle(self, url: str) -> bool:
        return True

    def parse(self, raw_html: str, crawl_markdown: str, url: str) -> str:
        return crawl_markdown


_FALLBACK = _FallbackParser()


def get_parser(url: str) -> BaseParser:
    """Return the first parser that can handle *url*, or the fallback."""
    for parser in _PARSERS:
        if parser.can_handle(url):
            return parser
    return _FALLBACK
