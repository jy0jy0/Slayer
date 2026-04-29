"""section_extractor 단위 테스트.

API 호출 없이 순수 마크다운 파싱 로직만 검증.

실행:
    uv run pytest tests/pipelines/test_section_extractor.py -v
"""

from __future__ import annotations

import pytest

from slayer.pipelines.jd_parser.section_extractor import (
    _find_role_anchors,
    _lcs_ratio,
    _match_role,
    extract_role_section,
)

# ── 픽스처 ─────────────────────────────────────────────────────────────────

MULTI_ROLE_MD = """\
## [효성ITX㈜](https://www.jobkorea.co.kr/company/xxx)
# 효성ITX AI 엔지니어 공개채용
상세요강접수기간∙방법기업정보

| 효성ITX㈜ AI 엔지니어 공개채용 |
| **AI DevOps 엔지니어**
( 2명 )   |
|  **담당업무**
ㆍCI/CD 파이프라인 구축 및 자동화
ㆍKubernetes 기반 AI 서비스 배포 및 운영
ㆍGitHub Actions, ArgoCD를 활용한 자동화 구축
ㆍAI 모델 서빙 인프라 구축 및 운영
ㆍ장애 대응 및 모니터링 체계 수립
**자격요건**
ㆍPython 3년 이상
ㆍDocker/K8s 실무 경험
ㆍLinux 서버 운영 경험
**우대사항**
ㆍGitOps 경험
ㆍTerraform 등 IaC 도구 사용 경험  |
| --- |

| **AI MLOps 엔지니어**
( 1명 )   |
|  **담당업무**
ㆍMLflow, Kubeflow 등 MLOps 플랫폼 구축
ㆍ모델 학습 파이프라인 자동화
ㆍ피처 스토어 설계 및 운영
ㆍ모델 성능 모니터링 및 재학습 자동화
ㆍ데이터 버전 관리 시스템 운영
**자격요건**
ㆍML 모델 서빙 경험 2년 이상
ㆍPython 기반 모델 개발 경험
ㆍScikit-learn, PyTorch 활용 경험
**우대사항**
ㆍ논문 구현 경험
ㆍKaggle 등 대회 수상 경험  |
| --- |

채용정보에 잘못된 내용이 있을 경우 문의해주세요.
모집요강
모집분야
AI DevOps 엔지니어 / AI MLOps 엔지니어
모집인원3명
고용형태
정규직
접수기간 · 방법
마감일
2026.04.30(목)
지원자 현황 통계
지원자 수
50 명
"""

SINGLE_ROLE_MD = """\
## [메타빌드㈜](https://www.jobkorea.co.kr/company/xxx)
# [메타빌드] AI Engineer 신입/경력 채용

| **AI Engineer**
( ○명 )   |
|  **담당업무** ㆍLLM/RAG/Agent 개발
**자격요건** ㆍPython 기본 역량  |
| --- |

채용정보에 잘못된 내용이 있을 경우 문의해주세요.
모집요강
모집분야
AI Engineer
마감일
2026.04.04(토)
지원자 현황 통계
"""


# ── _find_role_anchors ─────────────────────────────────────────────────────

def test_find_anchors_multi_role():
    anchors = _find_role_anchors(MULTI_ROLE_MD)
    names = [name for _, name in anchors]
    assert "AI DevOps 엔지니어" in names
    assert "AI MLOps 엔지니어" in names
    assert len(anchors) == 2


def test_find_anchors_single_role():
    anchors = _find_role_anchors(SINGLE_ROLE_MD)
    assert len(anchors) == 1


# ── _lcs_ratio ─────────────────────────────────────────────────────────────

def test_lcs_exact_match():
    assert _lcs_ratio("AI DevOps 엔지니어", "AI DevOps 엔지니어") == 1.0


def test_lcs_partial_overlap():
    score = _lcs_ratio("AI DevOps 엔지니어", "AI MLOps 엔지니어")
    assert 0.0 < score < 1.0


def test_lcs_no_overlap():
    assert _lcs_ratio("백엔드 개발자", "프론트엔드 디자이너") < 0.5


def test_lcs_empty():
    assert _lcs_ratio("", "AI 엔지니어") == 0.0


# ── _match_role ────────────────────────────────────────────────────────────

def test_match_role_exact():
    anchors = _find_role_anchors(MULTI_ROLE_MD)
    idx, score = _match_role(anchors, "AI DevOps 엔지니어")
    assert score == 1.0
    assert anchors[idx][1] == "AI DevOps 엔지니어"


def test_match_role_mlops():
    anchors = _find_role_anchors(MULTI_ROLE_MD)
    idx, score = _match_role(anchors, "AI MLOps 엔지니어")
    assert score == 1.0
    assert anchors[idx][1] == "AI MLOps 엔지니어"


# ── extract_role_section ───────────────────────────────────────────────────

def test_extract_devops_section():
    result = extract_role_section(MULTI_ROLE_MD, "AI DevOps 엔지니어")
    assert "CI/CD 파이프라인" in result          # DevOps 내용 포함
    assert "MLflow" not in result               # MLOps 내용 제외
    assert "AI DevOps 엔지니어" in result


def test_extract_mlops_section():
    result = extract_role_section(MULTI_ROLE_MD, "AI MLOps 엔지니어")
    assert "MLflow" in result                   # MLOps 내용 포함
    assert "CI/CD 파이프라인" not in result      # DevOps 내용 제외
    assert "AI MLOps 엔지니어" in result


def test_extract_includes_header():
    result = extract_role_section(MULTI_ROLE_MD, "AI DevOps 엔지니어")
    assert "효성ITX㈜" in result
    assert "효성ITX AI 엔지니어 공개채용" in result


def test_extract_includes_sidebar():
    result = extract_role_section(MULTI_ROLE_MD, "AI DevOps 엔지니어")
    assert "2026.04.30" in result               # deadline이 sidebar에서 포함


def test_single_role_passthrough():
    """단일 직무 공고는 원본 그대로 반환."""
    result = extract_role_section(SINGLE_ROLE_MD, "AI Engineer")
    assert result == SINGLE_ROLE_MD


def test_no_job_title_match_returns_original():
    """매칭되는 직무가 없으면 원본 반환."""
    result = extract_role_section(MULTI_ROLE_MD, "완전히다른직무XYZ")
    assert result == MULTI_ROLE_MD


def test_empty_markdown_returns_original():
    result = extract_role_section("", "AI 엔지니어")
    assert result == ""
