"""Tests for JSON parsing utilities."""
import json
import pytest

from mini_agent.core.utils.json_utils import (
    strip_code_fences,
    try_parse_json,
)


class TestStripCodeFences:
    def test_no_fences(self):
        assert strip_code_fences("hello") == "hello"

    def test_with_json_fences(self):
        raw = "```json\n{\"key\": \"value\"}\n```"
        assert strip_code_fences(raw) == '{"key": "value"}'

    def test_with_plain_fences(self):
        raw = "```\n{\"key\": \"value\"}\n```"
        assert strip_code_fences(raw) == '{"key": "value"}'

    def test_with_preamble_no_fences(self):
        raw = '{"key": "value"}'
        assert strip_code_fences(raw) == raw

    def test_empty_string(self):
        assert strip_code_fences("") == ""

    def test_fences_with_spaces_only(self):
        raw = "```json   \n{\"a\": 1}\n   ```"
        result = strip_code_fences(raw)
        assert result == '{"a": 1}'


class TestTryParseJson:
    def test_parse_simple_dict(self):
        result = try_parse_json('{"final_answer": "hello"}')
        assert result == {"final_answer": "hello"}

    def test_parse_with_fences(self):
        raw = "```json\n{\"final_answer\": \"hello\"}\n```"
        result = try_parse_json(raw)
        assert result == {"final_answer": "hello"}

    def test_parse_list(self):
        result = try_parse_json("[1, 2, 3]")
        assert result == [1, 2, 3]

    def test_parse_invalid_json(self):
        result = try_parse_json("this is not json")
        assert result is None

    def test_parse_none(self):
        assert try_parse_json(None) is None

    def test_parse_empty(self):
        assert try_parse_json("") is None

    def test_parse_with_trailing_text(self):
        """JSON with trailing non-JSON text should fail to parse."""
        result = try_parse_json('{"a": 1} extra text')
        assert result is None

    def test_parse_json_with_unicode(self):
        result = try_parse_json('{"message": "héllo"}')
        assert result == {"message": "héllo"}

    def test_realistic_agent_response(self):
        raw = '{\n  "final_answer": "The answer is 42."\n}'
        result = try_parse_json(raw)
        assert result == {"final_answer": "The answer is 42."}

    def test_parse_tool_call(self):
        raw = '{"tool_call": "web_search", "arguments": {"q": "test"}}'
        result = try_parse_json(raw)
        assert result == {"tool_call": "web_search", "arguments": {"q": "test"}}
