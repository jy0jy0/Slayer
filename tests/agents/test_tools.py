"""Unit tests for deterministic agent tools."""

import json
from slayer.agents.company_research.tools import validate_research_data
from slayer.agents.shared_tools import validate_json_output


class TestValidateResearchData:
    def test_valid_corp_info(self):
        data = json.dumps({"corp_name": "카카오", "ceo": "정신아", "employee_count": "4028", "industry": "IT", "corp_reg_no": "123"})
        result = json.loads(validate_research_data.invoke({"data_source": "corp_info", "result_json": data}))
        assert result["is_valid"] is True
        assert result["completeness_score"] == 1.0

    def test_empty_corp_info(self):
        result = json.loads(validate_research_data.invoke({"data_source": "corp_info", "result_json": "{}"}))
        assert result["is_valid"] is False
        assert result["completeness_score"] == 0.0

    def test_invalid_json(self):
        result = json.loads(validate_research_data.invoke({"data_source": "corp_info", "result_json": "not json"}))
        assert result["is_valid"] is False

    def test_non_dict_json(self):
        result = json.loads(validate_research_data.invoke({"data_source": "corp_info", "result_json": "[1,2,3]"}))
        assert result["is_valid"] is False

    def test_news_with_articles(self):
        data = json.dumps({"articles": [{"title": "test"}, {"title": "test2"}]})
        result = json.loads(validate_research_data.invoke({"data_source": "news", "result_json": data}))
        assert result["is_valid"] is True
        assert result["completeness_score"] == 0.4

    def test_financial_partial(self):
        data = json.dumps({"revenue": "100", "operating_profit": "50"})
        result = json.loads(validate_research_data.invoke({"data_source": "financial_info", "result_json": data}))
        assert result["is_valid"] is True
        assert result["completeness_score"] == 0.5


class TestValidateJsonOutput:
    def test_valid_match_result(self):
        data = json.dumps({"ats_score": 75, "matched_keywords": ["python"]})
        result = json.loads(validate_json_output.invoke({"json_str": data, "expected_schema_name": "match_result"}))
        assert result["is_valid"] is True

    def test_missing_required(self):
        result = json.loads(validate_json_output.invoke({"json_str": "{}", "expected_schema_name": "match_result"}))
        assert result["is_valid"] is False
        assert any("ats_score" in e for e in result["errors"])

    def test_invalid_json(self):
        result = json.loads(validate_json_output.invoke({"json_str": "broken", "expected_schema_name": "match_result"}))
        assert result["is_valid"] is False

    def test_non_dict(self):
        result = json.loads(validate_json_output.invoke({"json_str": "[1]", "expected_schema_name": "match_result"}))
        assert result["is_valid"] is False

    def test_unknown_schema(self):
        result = json.loads(validate_json_output.invoke({"json_str": "{}", "expected_schema_name": "unknown"}))
        assert result["is_valid"] is False


class TestParseAgentJson:
    def test_raw_json(self):
        from slayer.llm import parse_agent_json
        assert parse_agent_json('{"key": "value"}') == '{"key": "value"}'

    def test_json_in_markdown(self):
        from slayer.llm import parse_agent_json
        content = '```json\n{"key": "value"}\n```'
        assert '"key"' in parse_agent_json(content)

    def test_json_in_text(self):
        from slayer.llm import parse_agent_json
        content = 'Here is the result: {"key": "value"} end'
        assert '"key"' in parse_agent_json(content)

    def test_no_json_raises(self):
        from slayer.llm import parse_agent_json
        import pytest
        with pytest.raises(ValueError):
            parse_agent_json("no json here at all")

    def test_empty_raises(self):
        from slayer.llm import parse_agent_json
        import pytest
        with pytest.raises(ValueError):
            parse_agent_json("")
