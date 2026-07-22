"""Tests for the Agent class."""
import pytest
from mini_agent.core.agent import Agent
from mini_agent.registry.tools import Tool
from tests.mock_provider import MockLLMProvider


class TestAgentCreation:
    def test_agent_has_unique_id(self):
        agent = Agent(
            role="test_agent",
            instructions="Do something",
            llm_provider=MockLLMProvider(),
        )
        assert agent.id.startswith("test_agent_")
        assert len(agent.id) > len("test_agent_")

    def test_agent_default_state(self):
        agent = Agent(
            role="worker",
            instructions="Work",
            llm_provider=MockLLMProvider(),
        )
        assert agent.status == "idle"
        assert agent.tools == []
        assert agent.depth == 0


class TestAgentRun:
    def test_agent_returns_response_dict(self):
        llm = MockLLMProvider(responses=['{"final_answer": "task complete"}'])
        agent = Agent(
            role="worker",
            instructions="Do the task",
            llm_provider=llm,
        )
        result = agent.run()
        assert "response" in result
        assert "tool_calls" in result
        assert result["response"] == "task complete"

    def test_agent_status_changes(self):
        llm = MockLLMProvider(responses=['{"final_answer": "done"}'])
        agent = Agent(
            role="worker",
            instructions="Work",
            llm_provider=llm,
        )
        assert agent.status == "idle"
        agent.run()
        assert agent.status == "done"

    def test_agent_with_tools(self):
        def search(q):
            return f"result: {q}"

        t = Tool(name="web_search", description="Search", func=search, read_only=True)
        llm = MockLLMProvider(responses=[
            '{"tool_call": "web_search", "arguments": {"q": "test"}}',
            '{"final_answer": "found it"}',
        ])
        agent = Agent(
            role="researcher",
            instructions="Search for test",
            llm_provider=llm,
            tools=[t],
        )
        result = agent.run()
        assert result["response"] == "found it"
        assert len(result["tool_calls"]) == 1

    def test_agent_with_session_memory(self):
        llm = MockLLMProvider(responses=['{"final_answer": "done"}'])
        agent = Agent(
            role="worker",
            instructions="Work",
            llm_provider=llm,
            session_memory="Previous context here",
        )
        agent.run()
        # Check that session_memory was included in the system prompt
        assert any("Previous context here" in p for p in llm.system_prompts)

    def test_agent_with_skills_context(self):
        llm = MockLLMProvider(responses=['{"final_answer": "done"}'])
        agent = Agent(
            role="worker",
            instructions="Work",
            llm_provider=llm,
            skills_context="### Skill: Python dev",
        )
        agent.run()
        assert any("Python dev" in p for p in llm.system_prompts)


class TestAgentEdgeCases:
    def test_agent_error_in_run(self):
        """Agent handles LLM failures gracefully."""
        class FailingProvider(MockLLMProvider):
            def generate(self, system_prompt, user_message):
                raise RuntimeError("LLM crash")

        agent = Agent(
            role="worker",
            instructions="Do work",
            llm_provider=FailingProvider(),
        )
        result = agent.run()
        assert "response" in result
        assert "tool_calls" in result

    def test_agent_no_tools(self):
        """Agent with no tools can still answer."""
        llm = MockLLMProvider(responses=['{"final_answer": "no tools needed"}'])
        agent = Agent(
            role="thinker",
            instructions="Just think",
            llm_provider=llm,
            tools=[],
        )
        result = agent.run()
        assert result["response"] == "no tools needed"
