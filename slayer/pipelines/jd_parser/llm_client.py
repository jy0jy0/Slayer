"""Gemini 기반 LLM 추출 엔진.

담당: 현지
"""

from __future__ import annotations

import logging
import re

from google import genai
from google.genai import types

from slayer.config import GOOGLE_API_KEY
from slayer.schemas import JDSchema

logger = logging.getLogger(__name__)

_MODEL = "gemini-2.5-flash"

# ── 프롬프트 ──────────────────────────────────────────────

_JD_EXTRACT_PROMPT = """\
아래 텍스트는 채용 사이트에서 가져온 전체 페이지 내용입니다.
이미지가 함께 제공된 경우, 이미지에 포함된 채용 공고 내용도 함께 추출하세요.

## 당신의 역할
채용 공고 본문만 추출하여 **정형화된 JSON**으로 반환합니다.

## 규칙 (반드시 지켜주세요)
1. 채용 공고에 해당하는 내용만 추출하세요.
2. **원문의 텍스트를 그대로 유지하세요. 단어 하나도 바꾸거나 추가하지 마세요.**
3. 아래 항목은 반드시 제거하세요:
   - 사이트 메뉴, 네비게이션 링크
   - 광고, 배너
   - "추천공고", "비슷한 공고" 등 다른 공고 목록
   - 푸터 (저작권, 고객센터, 이용약관 등)
   - "로그인/회원가입" 관련 안내
4. 원문에 없는 내용을 절대 추가하지 마세요.
5. 해당 정보가 원문에 없으면 해당 필드는 비워두세요.
6. 이미지 안의 텍스트도 **그대로** 읽어서 적절한 필드에 배치하세요.
7. 텍스트와 이미지 모두에 같은 정보가 있으면 중복 없이 하나만 포함하세요.
{job_title_instruction}
## 입력 텍스트
{crawl_markdown}
"""

_JOB_TITLE_INSTRUCTION = """
## 직무 필터
이 페이지에 여러 모집부문이 있습니다.
**"{job_title}"** 모집부문에 해당하는 내용만 추출하세요.
다른 모집부문의 업무, 자격요건, 우대사항 등은 모두 제외하세요.
공통사항(전형방법, 접수기간 등)은 포함하세요.
"""


# ── 클라이언트 ────────────────────────────────────────────

def _get_client() -> genai.Client:
    """Gemini 클라이언트 생성."""
    if not GOOGLE_API_KEY:
        raise ValueError(
            "GOOGLE_API_KEY 환경 변수가 설정되지 않았습니다. "
            ".env 파일이나 시스템 환경 변수를 확인하세요."
        )
    return genai.Client(api_key=GOOGLE_API_KEY)


def verify_extraction(original: str, extracted: dict) -> list[str]:
    """추출 결과에 원본에 없는 내용이 있는지 검증 (Hallucination 감지).

    Args:
        original: crawl4ai 원본 Markdown.
        extracted: LLM이 추출한 JD dict.

    Returns:
        원본에 없는 의심 문장 리스트 (비어있으면 검증 통과).
    """
    original_words = set(re.findall(r'[가-힣a-zA-Z0-9]{3,}', original))

    texts: list[str] = []

    def _collect(obj):
        if isinstance(obj, str) and len(obj) >= 10:
            texts.append(obj)
        elif isinstance(obj, list):
            for item in obj:
                _collect(item)
        elif isinstance(obj, dict):
            for v in obj.values():
                _collect(v)

    _collect(extracted)

    suspicious: list[str] = []
    for text in texts:
        line_words = set(re.findall(r'[가-힣a-zA-Z0-9]{3,}', text))
        if not line_words:
            continue
        missing = line_words - original_words
        missing_ratio = len(missing) / len(line_words)
        if missing_ratio > 0.5 and len(missing) >= 2:
            suspicious.append(text)

    return suspicious


def extract_jd(
    crawl_markdown: str,
    image_urls: list[str] | None = None,
    save_dir: str | None = None,
    job_title: str | None = None,
) -> JDSchema:
    """crawl4ai Markdown(및 이미지)에서 JD 내용을 추출하여 JDSchema로 반환.

    Args:
        crawl_markdown: crawl4ai가 변환한 전체 페이지 Markdown.
        image_urls: JD 본문 이미지 URL 리스트 (None이면 텍스트만 처리).
        save_dir: 이미지를 저장할 디렉토리 경로 (None이면 저장 안 함).
        job_title: 특정 직무만 필터링할 직무명 (None이면 전체 추출).

    Returns:
        정형화된 JDSchema 객체.
    """
    import httpx
    from pathlib import Path

    client = _get_client()

    job_title_instruction = ""
    if job_title:
        job_title_instruction = _JOB_TITLE_INSTRUCTION.format(job_title=job_title)
        logger.info("직무 필터 적용: %s", job_title)

    prompt = _JD_EXTRACT_PROMPT.format(
        crawl_markdown=crawl_markdown,
        job_title_instruction=job_title_instruction,
    )

    contents: list = [prompt]

    if image_urls:
        for i, url in enumerate(image_urls):
            try:
                logger.info("이미지 다운로드 중: %s", url[:80])
                resp = httpx.get(url, timeout=30.0, follow_redirects=True)
                resp.raise_for_status()

                content_type = resp.headers.get("content-type", "image/jpeg")
                if "png" in content_type:
                    mime_type, ext = "image/png", ".png"
                elif "gif" in content_type:
                    mime_type, ext = "image/gif", ".gif"
                elif "webp" in content_type:
                    mime_type, ext = "image/webp", ".webp"
                else:
                    mime_type, ext = "image/jpeg", ".jpg"

                contents.append(types.Part.from_bytes(data=resp.content, mime_type=mime_type))
                logger.info("이미지 추가: %s (%d bytes)", mime_type, len(resp.content))

                if save_dir:
                    img_dir = Path(save_dir)
                    img_dir.mkdir(parents=True, exist_ok=True)
                    (img_dir / f"jd_image_{i+1}{ext}").write_bytes(resp.content)

            except Exception as exc:
                logger.error("이미지 다운로드 실패 (%s): %s", url[:80], exc)

    response = client.models.generate_content(
        model=_MODEL,
        contents=contents,
        config=types.GenerateContentConfig(
            temperature=0.0,
            top_p=0.1,
            response_mime_type="application/json",
            response_schema=JDSchema,
        ),
    )

    return JDSchema.model_validate_json(response.text)
