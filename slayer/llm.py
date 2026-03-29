"""공용 LLM Provider 모듈.

모든 에이전트/파이프라인에서 LLM 호출 시 이 모듈을 사용합니다.
LLMProvider Protocol 패턴으로 구현체 교체가 용이합니다.

사용 예시:
    from slayer.llm import get_default_provider
    provider = get_default_provider()
    result = provider.generate_json(prompt)
"""

from __future__ import annotations

import json
import logging
import os
from typing import Protocol, runtime_checkable

from openai import OpenAI

from slayer.config import OPENAI_API_KEY

logger = logging.getLogger(__name__)

# config.py에 OPENAI_MODEL = "gpt-5-mini"로 되어 있으나
# 실제 사용 가능한 모델로 환경변수 오버라이드 가능
LLM_MODEL = os.environ.get("SLAYER_LLM_MODEL", "gpt-4o-mini")


@runtime_checkable
class LLMProvider(Protocol):
    """JSON 응답을 반환하는 LLM 공통 인터페이스."""

    def generate_json(self, prompt: str, system_message: str | None = None) -> str:
        """프롬프트를 받아 JSON 문자열을 반환한다."""
        ...


class OpenAIProvider:
    """OpenAI API 기반 LLM Provider."""

    def __init__(self, model: str | None = None, api_key: str | None = None):
        key = api_key or OPENAI_API_KEY
        if not key:
            raise ValueError("OPENAI_API_KEY가 설정되지 않았습니다.")
        self.client = OpenAI(api_key=key)
        self.model = model or LLM_MODEL

    def generate_json(self, prompt: str, system_message: str | None = None) -> str:
        """프롬프트를 받아 JSON 문자열을 반환한다."""
        messages = []
        if system_message:
            messages.append({"role": "system", "content": system_message})
        messages.append({"role": "user", "content": prompt})

        logger.debug("LLM 호출 (model=%s)", self.model)
        response = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            response_format={"type": "json_object"},
        )
        content = response.choices[0].message.content or "{}"
        logger.debug("LLM 응답 수신 (%d chars)", len(content))
        return content


def get_default_provider() -> OpenAIProvider:
    """기본 LLM Provider 인스턴스를 반환한다."""
    return OpenAIProvider()


def get_chat_model(model: str = "gpt-4o-mini"):
    """LangGraph create_react_agent 용 ChatOpenAI 인스턴스."""
    from langchain_openai import ChatOpenAI

    if not OPENAI_API_KEY:
        raise ValueError("OPENAI_API_KEY가 설정되지 않았습니다.")
    return ChatOpenAI(model=model, api_key=OPENAI_API_KEY)
