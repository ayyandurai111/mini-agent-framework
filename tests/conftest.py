"""Pytest configuration and shared fixtures."""
import json
import os
import sys
import tempfile

import pytest

from tests.mock_provider import MockLLMProvider
from mini_agent import Orchestrator, ActionTracker
from mini_agent.registry.tools import Tool, ToolRegistry


@pytest.fixture
def mock_llm():
    return MockLLMProvider()


@pytest.fixture
def mock_llm_direct():
    """Returns a mock LLM that answers simple questions directly."""
    return MockLLMProvider(responses=['{"final_answer": "42"}'])


@pytest.fixture
def mock_llm_plan():
    """Returns a mock LLM that produces a multi-agent plan."""
    return MockLLMProvider(responses=[
        json.dumps({
            "needs_sub_agents": True,
            "sub_tasks": [
                {
                    "role": "researcher",
                    "instructions": "Research the topic",
                    "required_capabilities": ["web_search"],
                    "skill": "",
                    "depends_on": [],
                    "memory": False,
                },
                {
                    "role": "writer",
                    "instructions": "Write the report",
                    "required_capabilities": ["write_text_file"],
                    "skill": "",
                    "depends_on": [0],
                    "memory": True,
                },
            ],
        }),
        # First agent (researcher)
        '{"final_answer": "research complete"}',
        # Second agent (writer)
        '{"final_answer": "report written"}',
        # Aggregator
        '{"final_answer": "final aggregated answer"}',
    ])


@pytest.fixture
def mock_llm_single_agent():
    """Returns a mock LLM that says no sub-agents needed but requires a direct agent."""
    return MockLLMProvider(responses=[
        json.dumps({
            "needs_sub_agents": False,
            "required_capabilities": ["web_search"],
            "sub_tasks": [],
        }),
        '{"final_answer": "single agent answer"}',
    ])


@pytest.fixture
def sample_tools():
    tool_registry = ToolRegistry()
    tool_registry.register(Tool(
        name="web_search",
        description="Search the web",
        func=lambda q: f"mock result for {q}",
        read_only=True,
    ))
    tool_registry.register(Tool(
        name="write_text_file",
        description="Write text to a file",
        func=lambda path, content: f"wrote {len(content)} bytes to {path}",
        read_only=False,
    ))
    tool_registry.register(Tool(
        name="read_file",
        description="Read a file",
        func=lambda path: f"content of {path}",
        read_only=True,
    ))
    return tool_registry


@pytest.fixture
def orch(mock_llm_direct):
    """Basic orchestrator with mock LLM that answers directly."""
    o = Orchestrator(mock_llm_direct)
    return o


@pytest.fixture
def orch_with_tools(mock_llm_direct, sample_tools):
    o = Orchestrator(mock_llm_direct)
    for t in sample_tools.list_available():
        o.register_tool(sample_tools.get(t))
    return o


@pytest.fixture
def temp_dir():
    with tempfile.TemporaryDirectory() as d:
        yield d


@pytest.fixture
def empty_action_tracker():
    events = []

    def collector(event_type, data):
        events.append((event_type, data))

    return ActionTracker(on_event=collector), events
