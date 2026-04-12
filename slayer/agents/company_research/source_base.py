"""BaseSource ABC.

Owner: Jiho
Migration: moved from feat/company-research branch.
"""

from __future__ import annotations

from abc import ABC, abstractmethod


class BaseSource(ABC):
    """Abstract base class for company-information collection sources."""

    @property
    @abstractmethod
    def source_name(self) -> str:
        ...

    @abstractmethod
    async def fetch(self, company_name: str, **kwargs) -> dict:
        ...
