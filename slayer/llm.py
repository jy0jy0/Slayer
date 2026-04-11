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

from slayer.config import GOOGLE_API_KEY, OPENAI_API_KEY

logger = logging.getLogger(__name__)

# OpenAI 키 있으면 gpt-4o-mini, 없으면 Gemini로 환경변수 오버라이드 가능
LLM_MODEL = os.environ.get("SLAYER_LLM_MODEL", "gpt-4o-mini")
GEMINI_MODEL = os.environ.get("SLAYER_GEMINI_MODEL", "gemini-2.5-flash")


@runtime_checkable
class LLMProvider(Protocol):
    """JSON 응답을 반환하는 LLM 공통 인터페이스."""

    def generate_json(self, prompt: str, system_message: str | None = None) -> str:
        """프롬프트를 받아 JSON 문자열을 반환한다."""
        ...


class OpenAIProvider:
    """OpenAI API 기반 LLM Provider."""

    def __init__(self, model: str | None = None, api_key: str | None = None):
        from openai import OpenAI
        key = api_key or OPENAI_API_KEY
        if not key:
            raise ValueError("OPENAI_API_KEY가 설정되지 않았습니다.")
        self.client = OpenAI(api_key=key)
        self.model = model or LLM_MODEL

    def generate_json(self, prompt: str, system_message: str | None = None) -> str:
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


class GeminiProvider:
    """Google Gemini API 기반 LLM Provider (OpenAI fallback)."""

    def __init__(self, model: str | None = None, api_key: str | None = None):
        from google import genai
        from google.genai.types import GenerateContentConfig
        key = api_key or GOOGLE_API_KEY
        if not key:
            raise ValueError("GOOGLE_API_KEY가 설정되지 않았습니다.")
        self._client = genai.Client(api_key=key)
        self._config_cls = GenerateContentConfig
        self.model = model or GEMINI_MODEL

    def generate_json(self, prompt: str, system_message: str | None = None) -> str:
        contents = prompt
        if system_message:
            contents = f"{system_message}\n\n{prompt}"

        logger.debug("Gemini 호출 (model=%s)", self.model)
        response = self._client.models.generate_content(
            model=self.model,
            contents=contents,
            config=self._config_cls(
                response_mime_type="application/json",
                temperature=0.0,
            ),
        )
        content = response.text or "{}"
        logger.debug("Gemini 응답 수신 (%d chars)", len(content))
        return content


def _has_openai_key() -> bool:
    """실제 유효한 OpenAI 키가 설정되어 있는지 확인."""
    return bool(OPENAI_API_KEY and not OPENAI_API_KEY.startswith("your-"))


def get_default_provider() -> OpenAIProvider | GeminiProvider:
    """기본 LLM Provider 반환. OpenAI 키 없으면 Gemini로 자동 fallback."""
    if _has_openai_key():
        return OpenAIProvider()
    if GOOGLE_API_KEY:
        logger.info("OPENAI_API_KEY 없음 — Gemini로 fallback")
        return GeminiProvider()
    raise ValueError("OPENAI_API_KEY 또는 GOOGLE_API_KEY 중 하나는 설정해야 합니다.")


def get_chat_model(model: str = "gpt-4o-mini"):
    """LangGraph create_react_agent 용 Chat 모델.

    OpenAI 키 있으면 ChatOpenAI, 없으면 ChatGoogleGenerativeAI로 자동 fallback.
    """
    if _has_openai_key():
        from langchain_openai import ChatOpenAI
        return ChatOpenAI(model=model, api_key=OPENAI_API_KEY)

    if GOOGLE_API_KEY:
        from langchain_google_genai import ChatGoogleGenerativeAI
        logger.info("OPENAI_API_KEY 없음 — ChatGoogleGenerativeAI(%s)로 fallback", GEMINI_MODEL)
        return ChatGoogleGenerativeAI(model=GEMINI_MODEL, google_api_key=GOOGLE_API_KEY)

    raise ValueError("OPENAI_API_KEY 또는 GOOGLE_API_KEY 중 하나는 설정해야 합니다.")


def _extract_text_from_content(content) -> str:
    """AIMessage.content가 str 또는 list[dict] 형태일 때 텍스트를 추출.

    Gemini via LangChain은 [{'type': 'text', 'text': '...'}] 형식으로 반환.
    OpenAI는 str 형식으로 반환.
    """
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = [p.get("text", "") for p in content if isinstance(p, dict) and p.get("type") == "text"]
        return "\n".join(parts)
    return str(content)


def parse_agent_json(content) -> str:
    """Extract JSON string from LLM agent response.

    Handles: ```json blocks, raw JSON, JSON embedded in text.
    content는 str 또는 Gemini 스타일 list[dict] 모두 허용.
    Raises ValueError if no valid JSON found.
    """
    content = _extract_text_from_content(content)
    if not content:
        raise ValueError("Empty or non-string content")
    content = content.strip()
    # Try ```json block first
    if "```json" in content:
        parts = content.split("```json")
        if len(parts) >= 2:
            json_part = parts[1].split("```")[0].strip()
            if json_part:
                return json_part
    # Try ```  block
    if "```" in content:
        parts = content.split("```")
        if len(parts) >= 3:
            json_part = parts[1].strip()
            if json_part.startswith("{"):
                return json_part
    # Try raw JSON
    if content.startswith("{"):
        return content
    # Try finding JSON in text
    if "{" not in content or "}" not in content:
        raise ValueError("No JSON object found in response")
    try:
        start = content.index("{")
        end = content.rindex("}") + 1
        return content[start:end]
    except ValueError:
        raise ValueError("Failed to extract JSON boundaries")
