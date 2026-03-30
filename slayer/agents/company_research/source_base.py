"""BaseSource ABC.

담당: 지호
마이그레이션: feat/company-research 에서 이동
"""

from __future__ import annotations

from abc import ABC, abstractmethod


class BaseSource(ABC):
    """기업 정보 수집 소스의 추상 베이스 클래스."""

    @property
    @abstractmethod
    def source_name(self) -> str:
        ...

    @abstractmethod
    async def fetch(self, company_name: str, **kwargs) -> dict:
        ...
