"""JD-이력서 매칭 분석.

NOTE: 현지님 프로덕션 매칭 구현으로 교체 예정.
현재는 지호의 이력서 최적화/자소서 테스트를 위한 기본 구현입니다.
"""
from __future__ import annotations

import json
import logging

from slayer.llm import get_default_provider
from slayer.schemas import JDSchema, MatchResult, ParsedResume

logger = logging.getLogger(__name__)

MATCH_PROMPT = """당신은 ATS(Applicant Tracking System) 전문가입니다.
아래 채용공고(JD)와 이력서를 분석하여 매칭 결과를 JSON으로 반환하세요.

## ATS 점수 산출 가중치
- ats_simulation: 0.30 (ATS 시뮬레이션)
- keywords: 0.25 (키워드 매칭)
- experience: 0.20 (경력 적합도)
- industry_specific: 0.15 (산업 특화)
- content: 0.05 (콘텐츠 품질)
- format: 0.03 (형식)
- errors: 0.02 (오류)

## 출력 JSON
{{
  "ats_score": 0-100 사이 숫자,
  "score_breakdown": {{"ats_simulation": ..., "keywords": ..., "experience": ..., "industry_specific": ..., "content": ..., "format": ..., "errors": ...}},
  "matched_keywords": ["매칭된 키워드 목록"],
  "missing_keywords": ["부족한 키워드 목록"],
  "strengths": ["강점 목록 (3-5개)"],
  "weaknesses": ["약점 목록 (3-5개)"],
  "gap_summary": "종합 갭 분석 요약 (2-3문장)"
}}

## 채용공고 (JD)
{jd_json}

## 이력서
{resume_json}
"""


async def match_jd_resume(jd: JDSchema, resume: ParsedResume) -> MatchResult:
    """JD와 이력서를 매칭 분석하여 MatchResult를 반환."""
    provider = get_default_provider()
    prompt = MATCH_PROMPT.format(
        jd_json=jd.model_dump_json(indent=2),
        resume_json=resume.model_dump_json(indent=2),
    )
    result_str = provider.generate_json(
        prompt, system_message="ATS 분석 전문가. JSON만 출력."
    )
    data = json.loads(result_str)
    return MatchResult(**data)


def create_mock_match_result() -> MatchResult:
    """테스트용 목 데이터."""
    return MatchResult(
        ats_score=62.0,
        score_breakdown={
            "ats_simulation": 18.0,
            "keywords": 15.0,
            "experience": 14.0,
            "industry_specific": 8.0,
            "content": 4.0,
            "format": 2.0,
            "errors": 1.0,
        },
        matched_keywords=["python", "fastapi", "docker", "postgresql", "git"],
        missing_keywords=["kubernetes", "aws", "terraform", "ci/cd", "monitoring"],
        strengths=[
            "Python 백엔드 개발 경험 풍부",
            "FastAPI 프로젝트 다수 수행",
            "데이터베이스 설계 경험",
        ],
        weaknesses=[
            "클라우드 인프라 경험 부족",
            "DevOps 관련 키워드 누락",
            "대규모 트래픽 처리 경험 미기재",
        ],
        gap_summary=(
            "백엔드 개발 핵심 역량은 갖추고 있으나, 클라우드/인프라 관련 경험이 "
            "JD 요구사항 대비 부족합니다. kubernetes, AWS, CI/CD 파이프라인 경험을 "
            "보강하면 매칭률이 크게 향상될 것입니다."
        ),
    )
