"""JD-이력서 매칭 테스트."""

from slayer.pipelines.jd_resume_matcher import create_mock_match_result
from slayer.schemas import MatchResult


def test_mock_match_result():
    """목 매칭 결과가 올바른 스키마를 반환하는지 확인."""
    result = create_mock_match_result()
    assert isinstance(result, MatchResult)
    assert 0 <= result.ats_score <= 100
    assert len(result.matched_keywords) > 0
    assert len(result.missing_keywords) > 0
    assert len(result.strengths) > 0
    assert len(result.weaknesses) > 0
    assert result.gap_summary != ""


def test_mock_match_result_score_breakdown():
    """점수 상세 가중치 합이 맞는지 확인."""
    result = create_mock_match_result()
    total = sum(result.score_breakdown.values())
    assert abs(total - result.ats_score) < 0.1
