"""이력서 파서 LLM 클라이언트 — Gemini / OpenAI 선택 및 fallback.

우선순위 결정 (SLAYER_PARSER_LLM 환경변수):
  SLAYER_PARSER_LLM=gemini  → Gemini 2.5 Flash 고정
  SLAYER_PARSER_LLM=openai  → GPT-4o-mini 고정
  미설정                    → API 키 자동 감지 (GOOGLE_API_KEY 있으면 Gemini, 없으면 OpenAI)

사용 예시:
    from slayer.pipelines.resume_parser.llm_client import generate_json, generate_structured

    # Pydantic 스키마 기반 structured output
    from slayer.schemas import ParsedResume
    result = generate_structured(text, schema=ParsedResume)
"""

from __future__ import annotations

import json
import logging
import os
from typing import Any, Type, TypeVar

from pydantic import BaseModel

from slayer.config import GOOGLE_API_KEY, OPENAI_API_KEY

logger = logging.getLogger(__name__)

_GEMINI_MODEL = "gemini-2.5-flash"
_OPENAI_MODEL = "gpt-4o-mini"

T = TypeVar("T", bound=BaseModel)

# "gemini" | "openai" | "" (자동 감지)
_PARSER_LLM = os.environ.get("SLAYER_PARSER_LLM", "").lower().strip()


def _check_keys() -> None:
    if not GOOGLE_API_KEY and not OPENAI_API_KEY:
        raise RuntimeError(
            "GOOGLE_API_KEY 또는 OPENAI_API_KEY 중 하나가 필요합니다. "
            ".env 파일을 확인하세요."
        )


def _using_gemini() -> bool:
    """사용할 LLM 결정.

    SLAYER_PARSER_LLM으로 선호 LLM 설정 가능.
    설정한 LLM의 키가 없으면 자동으로 반대쪽으로 fallback.
    """
    if _PARSER_LLM == "gemini":
        return bool(GOOGLE_API_KEY) or not bool(OPENAI_API_KEY)
    if _PARSER_LLM == "openai":
        return not bool(OPENAI_API_KEY) and bool(GOOGLE_API_KEY)
    # 미설정: GOOGLE_API_KEY 있으면 Gemini, 없으면 OpenAI
    return bool(GOOGLE_API_KEY)


# ── Structured output (Pydantic 스키마 기반) ─────────────────


def generate_structured(text: str, schema: Type[T], system_prompt: str = "") -> T:
    """텍스트 → Pydantic 모델 (structured output).

    Args:
        text: 파싱할 텍스트
        schema: 출력 Pydantic 모델 클래스
        system_prompt: 시스템 프롬프트 (선택)

    Returns:
        schema 인스턴스
    """
    _check_keys()

    if _using_gemini():
        return _structured_gemini(text, schema, system_prompt)
    else:
        return _structured_openai(text, schema, system_prompt)


def _structured_gemini(text: str, schema: Type[T], system_prompt: str) -> T:
    from google import genai
    from google.genai.types import GenerateContentConfig

    client = genai.Client(api_key=GOOGLE_API_KEY)
    logger.debug("Gemini structured output: schema=%s", schema.__name__)

    response = client.models.generate_content(
        model=_GEMINI_MODEL,
        contents=text,
        config=GenerateContentConfig(
            system_instruction=system_prompt or None,
            response_mime_type="application/json",
            response_schema=schema,
            temperature=0.0,
        ),
    )
    return schema.model_validate_json(response.text)


def _structured_openai(text: str, schema: Type[T], system_prompt: str) -> T:
    from openai import OpenAI

    client = OpenAI(api_key=OPENAI_API_KEY)
    schema_str = json.dumps(schema.model_json_schema(), ensure_ascii=False, indent=2)
    system = f"{system_prompt}\n\nOutput JSON must match this schema:\n{schema_str}"
    logger.debug("OpenAI structured output: schema=%s", schema.__name__)

    response = client.chat.completions.create(
        model=_OPENAI_MODEL,
        temperature=0.0,
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": text},
        ],
    )
    return schema.model_validate_json(response.choices[0].message.content)


# ── JSON output (스키마 없이, 프롬프트로만 지정) ─────────────


def generate_json(
    system_prompt: str,
    user_content: str,
    extra_data: Any = None,
) -> dict:
    """프롬프트 기반 JSON 응답 생성.

    Args:
        system_prompt: 역할 및 규칙 정의
        user_content: 사용자 입력 텍스트
        extra_data: user_content에 추가할 데이터 (dict/list → JSON 직렬화)

    Returns:
        파싱된 dict
    """
    _check_keys()

    if extra_data is not None:
        user_content = user_content + "\n" + json.dumps(extra_data, ensure_ascii=False, indent=2)

    if _using_gemini():
        return _json_gemini(system_prompt, user_content)
    else:
        return _json_openai(system_prompt, user_content)


def _json_gemini(system_prompt: str, user_content: str) -> dict:
    from google import genai
    from google.genai.types import GenerateContentConfig

    client = genai.Client(api_key=GOOGLE_API_KEY)
    logger.debug("Gemini JSON generation")

    response = client.models.generate_content(
        model=_GEMINI_MODEL,
        contents=user_content,
        config=GenerateContentConfig(
            system_instruction=system_prompt,
            response_mime_type="application/json",
            temperature=0.0,
        ),
    )
    return json.loads(response.text)


def _json_openai(system_prompt: str, user_content: str) -> dict:
    from openai import OpenAI

    client = OpenAI(api_key=OPENAI_API_KEY)
    logger.debug("OpenAI JSON generation")

    response = client.chat.completions.create(
        model=_OPENAI_MODEL,
        temperature=0.0,
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content},
        ],
    )
    return json.loads(response.choices[0].message.content)
