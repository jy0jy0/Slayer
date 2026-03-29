"""Company Research ReAct Agent tests."""

from slayer.agents.company_research.source_base import BaseSource
from slayer.agents.company_research.sources import CorpInfoSource, FinancialInfoSource, NaverNewsSource
from slayer.agents.company_research.agent import build_company_research_agent
from slayer.schemas import CompanyResearchOutput


def test_source_classes_exist():
    assert issubclass(NaverNewsSource, BaseSource)
    assert issubclass(CorpInfoSource, BaseSource)
    assert issubclass(FinancialInfoSource, BaseSource)


def test_source_names():
    assert NaverNewsSource().source_name == "naver_news"
    assert CorpInfoSource().source_name == "corp_info"
    assert FinancialInfoSource().source_name == "financial_info"


def test_react_agent_builds():
    """ReAct agent graph builds successfully."""
    agent = build_company_research_agent()
    assert agent is not None
    assert type(agent).__name__ == "CompiledStateGraph"


def test_company_research_output_schema():
    output = CompanyResearchOutput(
        company_name="테스트",
        summary="테스트 요약",
        researched_at="2026-01-01T00:00:00",
    )
    assert output.company_name == "테스트"
    assert output.data_sources == []
