"""Gemini 기반 LLM 추출 엔진.

담당: 현지
"""

from __future__ import annotations

import logging
import re
import time

from google import genai
from google.genai import types
from pydantic import BaseModel

from slayer.config import GOOGLE_API_KEY
from slayer.schemas import JDSchema

logger = logging.getLogger(__name__)

_MODEL = "gemini-2.5-flash"
_MODEL_FALLBACK = "gemini-2.0-flash"
_RETRY_STATUS = ("503", "UNAVAILABLE")
# 429/RESOURCE_EXHAUSTED는 할당량 초과 → 짧은 backoff로 해결 안 됨, 즉시 fallback 모델로 전환
_QUOTA_STATUS = ("429", "RESOURCE_EXHAUSTED")

# ── 프롬프트 ──────────────────────────────────────────────

_JD_EXTRACT_PROMPT = """\
아래 텍스트는 채용 사이트에서 가져온 전체 페이지 내용입니다.

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
6. `deadline` 필드는 날짜만 추출하세요. "~", "까지", "접수마감", 요일 등 부가 텍스트는 제외합니다. (예: "2026.04.08")
7. `process` 필드는 채용 전형 단계명만 넣으세요. (예: ["서류전형", "1차 면접", "임원 면접", "최종합격"]) 법적 고지문, 서류 반환 안내, 합격자 통보 방식 등 부가 설명은 절대 포함하지 마세요.
{job_title_instruction}
## 입력 텍스트
{crawl_markdown}
"""

_JD_EXTRACT_PROMPT_IMAGE = """\
채용 공고 이미지가 첨부되어 있습니다.
아래 참고 텍스트는 페이지의 부수적인 정보(공고명, 마감일, 고용형태 등)만 포함하며, 실제 직무 내용(담당업무·자격요건·우대사항)은 이미지에만 있습니다.

## 당신의 역할
**첨부된 이미지를 직접 읽어서** 채용 공고 내용을 **정형화된 JSON**으로 반환합니다.

## 규칙 (반드시 지켜주세요)
1. **이미지에 실제로 적혀 있는 텍스트만 추출하세요.**
2. **이미지에 없는 내용은 절대 추가하지 마세요.** 직무명에서 연상되는 일반적인 내용(예: "Kubernetes", "경력 3년", "Jenkins" 등)을 임의로 채워 넣는 것은 엄격히 금지됩니다.
3. 해당 정보가 이미지에 없으면 해당 필드는 비워두세요.
4. 이미지 안의 텍스트를 **단어 하나도 바꾸지 말고** 그대로 읽어서 적절한 필드에 배치하세요.
5. `deadline` 필드는 날짜만 추출하세요. "~", "까지", "접수마감", 요일 등 부가 텍스트는 제외합니다. (예: "2026.04.08")
6. `process` 필드는 채용 전형 단계명만 넣으세요. (예: ["서류전형", "1차 면접", "임원 면접", "최종합격"]) 법적 고지문, 서류 반환 안내, 합격자 통보 방식 등 부가 설명은 절대 포함하지 마세요.
{job_title_instruction}
## 참고 텍스트 (부수 정보만)
{crawl_markdown}
"""

_JOB_TITLE_INSTRUCTION = """
## 직무 필터 (엄격히 적용)
이 페이지에 여러 모집부문이 있습니다.
**반드시 "{job_title}"** 모집부문에 해당하는 내용만 추출하세요.
{other_roles_block}
### 주의사항
- 이름이 비슷한 다른 직무가 있을 경우, **정확히 "{job_title}"인 것만** 추출하세요.
- 다른 모집부문의 업무내용, 자격요건, 우대사항은 **절대 포함하지 마세요**.
- 어느 직무에 속하는지 불분명한 항목은 제외하세요.
- 전형방법, 접수기간, 공통 복리후생처럼 모든 직무에 공통으로 적용되는 내용은 포함해도 됩니다.
"""

_IDENTIFY_ROLES_PROMPT = """\
이 이미지는 채용 공고입니다.
이미지에 포함된 모든 모집부문(직무) 제목을 찾아 목록으로 반환하세요.
예: {"roles": ["AI DevOps 엔지니어", "AI MLOps 엔지니어"]}
직무가 1개라면: {"roles": ["AI 엔지니어"]}
"""


class _RoleList(BaseModel):
    roles: list[str]


# ── 클라이언트 ────────────────────────────────────────────

def _generate_with_retry(
    client: genai.Client,
    contents: list,
    config: types.GenerateContentConfig,
    max_retries: int = 3,
):
    """503/429 등 일시적 오류에 대해 exponential backoff 재시도.
    primary 모델(_MODEL) 모두 실패 시 fallback 모델(_MODEL_FALLBACK)로 1회 추가 시도.
    """
    last_exc: Exception | None = None

    for model in (_MODEL, _MODEL_FALLBACK):
        for attempt in range(max_retries):
            try:
                return client.models.generate_content(
                    model=model, contents=contents, config=config
                )
            except Exception as exc:
                exc_str = str(exc)
                if any(s in exc_str for s in _QUOTA_STATUS):
                    # 할당량 초과: backoff 무의미, 즉시 다음 모델로 전환
                    last_exc = exc
                    logger.warning("Gemini API 할당량 초과 [%s], 다음 모델로 전환: %s", model, exc_str[:80])
                    break
                if not any(s in exc_str for s in _RETRY_STATUS):
                    raise  # 재시도해도 의미 없는 오류 (인증, 스키마 등)
                last_exc = exc
                if attempt < max_retries - 1:
                    wait = 2 ** attempt  # 1s → 2s → 4s
                    logger.warning(
                        "Gemini API 일시 오류 [%s] (시도 %d/%d), %ds 후 재시도: %s",
                        model, attempt + 1, max_retries, wait, exc_str[:80],
                    )
                    time.sleep(wait)
                else:
                    logger.warning("Gemini API [%s] %d회 모두 실패", model, max_retries)

    raise last_exc  # type: ignore[misc]


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
    original_words = {w.lower() for w in re.findall(r'[가-힣a-zA-Z0-9]{3,}', original)}

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
        line_words = {w.lower() for w in re.findall(r'[가-힣a-zA-Z0-9]{3,}', text)}
        if not line_words:
            continue
        missing = line_words - original_words
        missing_ratio = len(missing) / len(line_words)
        if missing_ratio > 0.5 and len(missing) >= 2:
            suspicious.append(text)

    return suspicious


def identify_roles_in_image(image_data: list[tuple[bytes, str]]) -> list[str]:
    """이미지에서 모집부문 이름 목록만 추출 (1차 호출, 저비용).

    이미지 기반 멀티-직무 공고에서 다른 직무를 명시적으로 배제하기 위해 사용.
    실패 시 빈 리스트 반환 (fail-open).

    Args:
        image_data: 미리 다운로드된 이미지 리스트. 각 항목은 (bytes, mime_type).
    """
    try:
        client = _get_client()
        contents: list = [_IDENTIFY_ROLES_PROMPT]
        for data, mime in image_data:
            contents.append(types.Part.from_bytes(data=data, mime_type=mime))
        response = _generate_with_retry(
            client, contents,
            types.GenerateContentConfig(
                temperature=0.0,
                response_mime_type="application/json",
                response_schema=_RoleList,
            ),
        )
        roles = _RoleList.model_validate_json(response.text).roles
        logger.info("이미지 직무 목록 파악: %s", roles)
        return roles
    except Exception:
        logger.exception("직무 목록 파악 실패, 단일 직무로 처리")
        return []


def download_images(
    image_urls: list[str],
    save_dir: str | None = None,
) -> list[tuple[bytes, str]]:
    """이미지 URL 리스트를 다운로드하여 (bytes, mime_type) 리스트로 반환.

    Args:
        image_urls: 다운로드할 이미지 URL 리스트.
        save_dir: 이미지를 파일로 저장할 디렉토리 (None이면 저장 안 함).

    Returns:
        각 이미지의 (bytes, mime_type) 튜플 리스트.
        다운로드 실패한 이미지는 결과에서 제외.
    """
    import httpx
    from pathlib import Path

    result: list[tuple[bytes, str]] = []
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

            result.append((resp.content, mime_type))
            logger.info("이미지 다운로드 완료: %s (%d bytes)", mime_type, len(resp.content))

            if save_dir:
                img_dir = Path(save_dir)
                img_dir.mkdir(parents=True, exist_ok=True)
                (img_dir / f"jd_image_{i+1}{ext}").write_bytes(resp.content)

        except Exception as exc:
            logger.error("이미지 다운로드 실패 (%s): %s", url[:80], exc)

    return result


def extract_jd(
    crawl_markdown: str,
    image_urls: list[str] | None = None,
    image_data: list[tuple[bytes, str]] | None = None,
    save_dir: str | None = None,
    job_title: str | None = None,
    other_roles: list[str] | None = None,
) -> JDSchema:
    """crawl4ai Markdown(및 이미지)에서 JD 내용을 추출하여 JDSchema로 반환.

    Args:
        crawl_markdown: crawl4ai가 변환한 전체 페이지 Markdown.
        image_urls: JD 본문 이미지 URL 리스트. image_data가 없을 때만 사용.
        image_data: 미리 다운로드된 이미지 리스트. 각 항목은 (bytes, mime_type).
                    제공되면 image_urls 다운로드를 건너뜀.
        save_dir: 이미지를 저장할 디렉토리 경로 (image_urls로 다운로드할 때만 적용).
        job_title: 특정 직무만 필터링할 직무명 (None이면 전체 추출).
        other_roles: 명시적으로 배제할 다른 직무명 리스트.

    Returns:
        정형화된 JDSchema 객체.
    """
    client = _get_client()

    job_title_instruction = ""
    if job_title:
        if other_roles:
            lines = "\n".join(f"- {r}" for r in other_roles)
            other_roles_block = f"\n### 이 공고의 다른 모집부문 (절대 포함 금지)\n{lines}\n"
        else:
            other_roles_block = ""
        job_title_instruction = _JOB_TITLE_INSTRUCTION.format(
            job_title=job_title, other_roles_block=other_roles_block
        )
        logger.info("직무 필터 적용: %s (배제 직무: %s)", job_title, other_roles or [])

    # image_data가 주어지면 재다운로드 없이 사용, 아니면 image_urls에서 다운로드
    images = image_data if image_data is not None else (
        download_images(image_urls, save_dir=save_dir) if image_urls else []
    )

    # 이미지 유무에 따라 프롬프트 분기
    # 이미지 기반 공고는 실제 JD 내용이 이미지에만 있으므로 전용 프롬프트 사용
    prompt_template = _JD_EXTRACT_PROMPT_IMAGE if images else _JD_EXTRACT_PROMPT
    prompt = prompt_template.format(
        crawl_markdown=crawl_markdown,
        job_title_instruction=job_title_instruction,
    )

    contents: list = [prompt]
    for data, mime in images:
        contents.append(types.Part.from_bytes(data=data, mime_type=mime))

    response = _generate_with_retry(
        client, contents,
        types.GenerateContentConfig(
            temperature=0.0,
            top_p=0.1,
            response_mime_type="application/json",
            response_schema=JDSchema,
        ),
    )

    return JDSchema.model_validate_json(response.text)
