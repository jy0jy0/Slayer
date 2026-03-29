"""면접 질문 생성 파이프라인용 LLM Provider.

LLMProvider Protocol을 구현하면 어떤 LLM이든 generator에 주입 가능.
기본값은 GeminiProvider.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from slayer.config import GOOGLE_API_KEY, OPENAI_API_KEY


@runtime_checkable
class LLMProvider(Protocol):
    """JSON 응답을 반환하는 LLM 공통 인터페이스."""

    def generate_json(self, prompt: str) -> str:
        """프롬프트를 받아 JSON 문자열을 반환한다."""
        ...


class GeminiProvider:
    """Google Gemini 기반 LLM Provider (기본값)."""

    def __init__(self, model: str = "gemini-2.5-flash", api_key: str = GOOGLE_API_KEY) -> None:
        from google import genai

        self._model = model
        self._client = genai.Client(api_key=api_key)

    def generate_json(self, prompt: str) -> str:
        from google.genai import types

        response = self._client.models.generate_content(
            model=self._model,
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
            ),
        )
        return response.text or "{}"


class OpenAIProvider:
    """OpenAI 기반 LLM Provider."""

    def __init__(self, model: str = "gpt-4o-mini", api_key: str = OPENAI_API_KEY) -> None:
        from openai import OpenAI

        self._model = model
        self._client = OpenAI(api_key=api_key)

    def generate_json(self, prompt: str) -> str:
        response = self._client.chat.completions.create(
            model=self._model,
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"},
        )
        return response.choices[0].message.content or "{}"
