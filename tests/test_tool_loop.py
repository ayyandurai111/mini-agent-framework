"""Tests for the ReAct tool execution loop."""
import pytest
from mini_agent.core.tool_loop import run_with_tools
from mini_agent.registry.tools import Tool
from tests.mock_provider import MockLLMProvider


def test_direct_final_answer():
    llm = MockLLMProvider(responses=['{"final_answer": "Hello world"}'])
    result = run_with_tools(
        llm_provider=llm,
        system_prompt="You are a test agent.",
        task="Say hello",
        tools=[],
        max_iterations=5,
    )
    assert result == "Hello world"


def test_return_parsed_dict():
    llm = MockLLMProvider(responses=['{"final_answer": "hello"}'])
    result = run_with_tools(
        llm_provider=llm,
        system_prompt="Test",
        task="Test task",
        tools=[],
        max_iterations=5,
        return_parsed=True,
    )
    assert result == {"final_answer": "hello"}


def test_custom_exit_key():
    llm = MockLLMProvider(responses=['{"needs_sub_agents": true}'])
    result = run_with_tools(
        llm_provider=llm,
        system_prompt="Test",
        task="Plan",
        tools=[],
        max_iterations=5,
        exit_keys=["needs_sub_agents", "final_answer"],
        return_parsed=True,
    )
    assert result == {"needs_sub_agents": True}


def test_tool_call_flow():
    def search(q):
        return f"Results for: {q}"

    search_tool = Tool(name="web_search", description="Search web", func=search, read_only=True)
    llm = MockLLMProvider(responses=[
        '{"tool_call": "web_search", "arguments": {"q": "test"}}',
        '{"final_answer": "Found results"}',
    ])

    result = run_with_tools(
        llm_provider=llm,
        system_prompt="Test",
        task="Search for test",
        tools=[search_tool],
        max_iterations=5,
    )
    assert result == "Found results"


def test_max_iterations_reached():
    def search(q):
        return "some result"

    search_tool = Tool(name="web_search", description="Search web", func=search, read_only=True)
    llm = MockLLMProvider(responses=[
        '{"tool_call": "web_search", "arguments": {"q": "t1"}}',
        '{"tool_call": "web_search", "arguments": {"q": "t2"}}',
        '{"tool_call": "web_search", "arguments": {"q": "t3"}}',
        '{"tool_call": "web_search", "arguments": {"q": "t4"}}',
        '{"tool_call": "web_search", "arguments": {"q": "t5"}}',
        '{"tool_call": "web_search", "arguments": {"q": "t6"}}',
    ])

    result = run_with_tools(
        llm_provider=llm,
        system_prompt="Test",
        task="Search",
        tools=[search_tool],
        max_iterations=5,
    )
    assert "Stopped after" in result
    assert "5 tool calls" in result


def test_tool_not_found():
    llm = MockLLMProvider(responses=[
        '{"tool_call": "nonexistent", "arguments": {}}',
        '{"final_answer": "done"}',
    ])

    result = run_with_tools(
        llm_provider=llm,
        system_prompt="Test",
        task="Test task",
        tools=[],
        max_iterations=5,
    )
    assert result == "done"


def test_undefined_tool_returns_error_message():
    llm = MockLLMProvider(responses=[
        '{"tool_call": "bad_tool", "arguments": {}}',
        '{"final_answer": "ok"}',
    ])

    history = []
    result = run_with_tools(
        llm_provider=llm,
        system_prompt="Test",
        task="Test task",
        tools=[],
        max_iterations=5,
        tool_history=history,
    )
    assert result == "ok"
    assert len(history) == 1
    assert "Error" in history[0]["result"]


def test_tool_history_populated():
    def my_tool(x):
        return x * 2

    t = Tool(name="double", description="Doubles input", func=my_tool, read_only=True)
    llm = MockLLMProvider(responses=[
        '{"tool_call": "double", "arguments": {"x": 21}}',
        '{"final_answer": "42"}',
    ])

    history = []
    result = run_with_tools(
        llm_provider=llm,
        system_prompt="Test",
        task="Double 21",
        tools=[t],
        max_iterations=5,
        tool_history=history,
    )
    assert result == "42"
    assert len(history) == 1
    assert history[0]["tool"] == "double"
    assert history[0]["arguments"] == {"x": 21}
    assert history[0]["result"] == "42"


def test_approval_callback_rejects():
    def dangerous(cmd):
        return f"ran: {cmd}"

    t = Tool(name="bash", description="Run command", func=dangerous, requires_approval=True)

    def reject(name, args):
        return False

    llm = MockLLMProvider(responses=[
        '{"tool_call": "bash", "arguments": {"cmd": "rm -rf /"}}',
        '{"final_answer": "ok"}',
    ])

    history = []
    result = run_with_tools(
        llm_provider=llm,
        system_prompt="Test",
        task="Run cmd",
        tools=[t],
        max_iterations=5,
        approval_callback=reject,
        tool_history=history,
    )
    assert result == "ok"
    assert "did not approve" in history[0]["result"]


def test_tool_run_error():
    def failing():
        raise ValueError("something broke")

    t = Tool(name="failing", description="Fails", func=failing, read_only=True)
    llm = MockLLMProvider(responses=[
        '{"tool_call": "failing", "arguments": {}}',
        '{"final_answer": "handled"}',
    ])

    history = []
    result = run_with_tools(
        llm_provider=llm,
        system_prompt="Test",
        task="Test",
        tools=[t],
        max_iterations=5,
        tool_history=history,
    )
    assert result == "handled"
    assert "Error running tool" in history[0]["result"]


def test_llm_call_error():
    class FailingProvider(MockLLMProvider):
        def generate(self, system_prompt, user_message):
            raise ConnectionError("API down")

    llm = FailingProvider()
    result = run_with_tools(
        llm_provider=llm,
        system_prompt="Test",
        task="Test",
        tools=[],
        max_iterations=5,
    )
    assert "LLM call failed" in result


def test_non_json_response():
    llm = MockLLMProvider(responses=["This is not JSON"])
    result = run_with_tools(
        llm_provider=llm,
        system_prompt="Test",
        task="Test task",
        tools=[],
        max_iterations=5,
    )
    assert result == "This is not JSON"
