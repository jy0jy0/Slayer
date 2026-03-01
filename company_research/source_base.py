from __future__ import annotations

from abc import ABC, abstractmethod


class BaseSource(ABC):
    """기업 정보 수집 소스의 추상 베이스 클래스."""

    @property
    @abstractmethod
    def source_name(self) -> str:
        """소스 식별 이름 (예: 'naver_news', 'corp_info')."""
        ...

    @abstractmethod
    async def fetch(self, company_name: str, **kwargs) -> dict:
        """회사명으로 데이터를 수집.

        Args:
            company_name: 검색할 회사명.
            **kwargs: 소스별 추가 파라미터.

        Returns:
            수집된 raw 데이터 dict.
            실패 시 빈 dict 또는 에러 정보 포함.
        """
        ...
