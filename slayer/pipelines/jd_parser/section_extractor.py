"""Multi-role JD section extractor for Jobkorea classic format.

담당: 현지

한 공고에 여러 직무가 있을 때 (예: AI DevOps 엔지니어, AI MLOps 엔지니어),
LLM 호출 전에 target 직무 섹션만 마크다운에서 잘라내어 반환한다.
섹션 경계를 감지하지 못하면 원본 마크다운을 그대로 반환 (fail-open).
"""

from __future__ import annotations

import logging
import re

logger = logging.getLogger(__name__)

# Jobkorea 클래식 표 형식에서 직무명 앵커 패턴
# 예: | **AI DevOps 엔지니어**   (다음 줄은 반드시 ( N명 ) 인원수 표기)
# lookahead (?=\n\s*\() 로 | **담당업무** 나 | **모집인원** 같은 오탐 방지
_ROLE_ANCHOR_RE = re.compile(
    r"^\|\s*\*\*([^\n*]{3,80})\*\*\s*$(?=\n\s*\()",
    re.MULTILINE,
)

_MIN_SECTION_LEN = 200  # 이 이하면 추출 실패로 간주
_MATCH_SCORE_THRESHOLD = 0.4


def extract_role_section(md_text: str, job_title: str) -> str:
    """target job_title 섹션만 반환. 실패 시 원본 반환 (fail-open).

    Args:
        md_text: Crawl4AI가 생성한 전체 마크다운
        job_title: 사용자가 지정한 직무명 (예: "AI DevOps 엔지니어")

    Returns:
        target 직무 섹션 마크다운 (헤더 + 섹션 본문 + 공통 sidebar 포함)
        감지 실패 시 원본 md_text 그대로 반환
    """
    try:
        anchors = _find_role_anchors(md_text)
        if len(anchors) < 2:
            logger.debug("직무 앵커 %d개 감지 (멀티-직무 아님), 원본 사용", len(anchors))
            return md_text

        best_idx, score = _match_role(anchors, job_title)
        if score < _MATCH_SCORE_THRESHOLD:
            logger.warning("직무명 매칭 실패 (최고 score=%.2f): %s", score, job_title)
            return md_text

        # 섹션 경계: matched anchor ~ 다음 anchor (또는 sidebar 시작)
        start_char = anchors[best_idx][0]
        if best_idx + 1 < len(anchors):
            end_char = anchors[best_idx + 1][0]
        else:
            sidebar_match = re.search(r"\n채용정보에 잘못된", md_text)
            end_char = sidebar_match.start() if sidebar_match else len(md_text)

        role_section = md_text[start_char:end_char].strip()
        if len(role_section) < _MIN_SECTION_LEN:
            logger.warning("추출 섹션이 너무 짧음 (%d자), 원본 사용", len(role_section))
            return md_text

        header = _extract_header(md_text)
        sidebar = _extract_sidebar(md_text)
        result = "\n\n".join(part for part in [header, role_section, sidebar] if part)

        logger.info(
            "섹션 추출 완료: %d자 → %d자 (직무: %s, score=%.2f)",
            len(md_text), len(result), job_title, score,
        )
        return result

    except Exception:
        logger.exception("섹션 추출 중 예외 발생, 원본 마크다운 사용")
        return md_text


def _find_role_anchors(md_text: str) -> list[tuple[int, str]]:
    """(char_offset, role_name) 리스트 반환."""
    return [(m.start(), m.group(1).strip()) for m in _ROLE_ANCHOR_RE.finditer(md_text)]


def _match_role(anchors: list[tuple[int, str]], job_title: str) -> tuple[int, float]:
    """가장 잘 매칭되는 anchor index와 score 반환 (대소문자 무시)."""
    best_idx, best_score = 0, 0.0
    job_lower = job_title.lower()
    for i, (_, name) in enumerate(anchors):
        name_lower = name.lower()
        if job_lower in name_lower or name_lower in job_lower:
            score = 1.0
        else:
            score = _lcs_ratio(job_lower, name_lower)
        if score > best_score:
            best_score, best_idx = score, i
    return best_idx, best_score


def _lcs_ratio(a: str, b: str) -> float:
    """Normalized longest common substring ratio.

    짧은 직무명 비교 전용 (O(n*m), 100자 이하에서 충분히 빠름).
    """
    if not a or not b:
        return 0.0
    m, n = len(a), len(b)
    dp = [[0] * (n + 1) for _ in range(2)]
    lcs_len = 0
    for i in range(1, m + 1):
        for j in range(1, n + 1):
            if a[i - 1] == b[j - 1]:
                dp[i % 2][j] = dp[(i - 1) % 2][j - 1] + 1
                lcs_len = max(lcs_len, dp[i % 2][j])
            else:
                dp[i % 2][j] = 0
    return lcs_len / max(m, n)


def _extract_header(md_text: str) -> str:
    """## 회사명 / # 공고명 줄 추출 (상위 5줄 내에서)."""
    header_lines = [
        line for line in md_text.splitlines()[:5]
        if line.startswith("## ") or line.startswith("# ")
    ]
    return "\n".join(header_lines)


def _extract_sidebar(md_text: str) -> str:
    """모집요강 블록(deadline, 고용형태 등 공통 필드) 추출."""
    match = re.search(r"\n(채용정보에 잘못된.*?)지원자 현황 통계", md_text, re.DOTALL)
    if match:
        return match.group(1).strip()
    match2 = re.search(r"\n채용정보에 잘못된", md_text)
    if match2:
        return md_text[match2.start():].strip()
    return ""
