"""Tests for the Orchestrator."""
import json
import pytest

from mini_agent import Orchestrator
from mini_agent.registry.tools import Tool
from tests.mock_provider import MockLLMProvider


class TestOrchestratorInit:
    def test_requires_llm_provider(self):
        with pytest.raises(ValueError, match="llm_provider"):
            Orchestrator(None)

    def test_default_initialization(self, mock_llm):
        o = Orchestrator(mock_llm)
        assert o.llm_provider is mock_llm
        assert o.tool_registry is not None
        assert o.skill_registry is not None
        assert o.action_tracker is not None

    def test_register_tool(self, mock_llm):
        o = Orchestrator(mock_llm)
        t = Tool(name="test", description="Test tool", func=lambda: None)
        o.register_tool(t)
        assert o.tool_registry.get("test") is t

    def test_register_tools_list(self, mock_llm):
        o = Orchestrator(mock_llm)
        t1 = Tool(name="a", description="A", func=lambda: None)
        t2 = Tool(name="b", description="B", func=lambda: None)
        o.register_tools([t1, t2])
        assert o.tool_registry.get("a") is t1
        assert o.tool_registry.get("b") is t2


class TestOrchestratorRun:
    def test_direct_answer(self, mock_llm_direct):
        o = Orchestrator(mock_llm_direct)
        result = o.run("What is 2+2?")
        assert result["final_answer"] == "42"
        assert "sub_agent_results" in result

    def test_direct_answer_persists_to_memory(self, mock_llm_direct, temp_dir):
        import os
        mem_file = os.path.join(temp_dir, "memory.json")
        o = Orchestrator(mock_llm_direct, memory_file=mem_file)
        o.run("Hello")
        assert len(o.conversation_memory._turns) == 1

    def test_single_agent_plan(self, mock_llm_single_agent):
        o = Orchestrator(mock_llm_single_agent)
        t = Tool(name="web_search", description="Search", func=lambda q: f"res: {q}", read_only=True)
        o.register_tool(t)
        result = o.run("Search for something")
        assert result["final_answer"] == "single agent answer"

    def test_multi_agent_plan(self, mock_llm_plan):
        o = Orchestrator(mock_llm_plan)
        t1 = Tool(name="web_search", description="Search", func=lambda q: f"res: {q}", read_only=True)
        t2 = Tool(name="write_text_file", description="Write file", func=lambda path, content: "ok", read_only=False)
        o.register_tools([t1, t2])
        result = o.run("Research and write a report")
        assert result["final_answer"] is not None

    def test_plan_fallback_on_error(self):
        class FailingProvider(MockLLMProvider):
            def generate(self, system_prompt, user_message):
                raise RuntimeError("LLM failure")

        llm = FailingProvider()
        o = Orchestrator(llm)
        o.register_tool(Tool(name="web_search", description="Search", func=lambda q: "res", read_only=True))
        result = o.run("Do something")
        assert "final_answer" in result

    def test_agent_execution_error(self, mock_llm_direct):
        class FakeTool:
            name = "failing"
            description = "Fails"
            requires_approval = False
            read_only = True
            def describe(self):
                return "failing() - fails"
            def run(self, **kwargs):
                raise ValueError("tool error")

        mock_llm_direct.responses = [
            json.dumps({"needs_sub_agents": False, "required_capabilities": ["failing"], "sub_tasks": []}),
            '{"final_answer": "ok"}',
        ]
        o = Orchestrator(mock_llm_direct)
        o.register_tool(FakeTool())
        result = o.run("Do something")
        assert "final_answer" in result

    def test_max_agents_respected(self):
        llm = MockLLMProvider(responses=[
            json.dumps({
                "needs_sub_agents": True,
                "sub_tasks": [
                    {"role": "a", "instructions": "task a", "required_capabilities": [], "depends_on": []},
                    {"role": "b", "instructions": "task b", "required_capabilities": [], "depends_on": []},
                    {"role": "c", "instructions": "task c", "required_capabilities": [], "depends_on": []},
                    {"role": "d", "instructions": "task d", "required_capabilities": [], "depends_on": []},
                    {"role": "e", "instructions": "task e", "required_capabilities": [], "depends_on": []},
                    {"role": "f", "instructions": "task f", "required_capabilities": [], "depends_on": []},
                ],
            }),
            '{"final_answer": "done"}',
            '{"final_answer": "done"}',
            '{"final_answer": "done"}',
            '{"final_answer": "aggregated"}',
        ])
        o = Orchestrator(llm, max_agents=3)
        result = o.run("Complex task")
        assert "final_answer" in result


class TestOrchestratorChat:
    def test_chat_returns_raw_response(self, mock_llm_direct):
        o = Orchestrator(mock_llm_direct)
        result = o.chat("Hello")
        assert result == '{"final_answer": "42"}'

    def test_chat_with_session(self, mock_llm_direct):
        from mini_agent import SessionManager
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            sm = SessionManager(sessions_dir=d)
            o = Orchestrator(mock_llm_direct, session_manager=sm)
            sid = sm.create_session("test_session")["id"]
            result = o.chat("Hello", session_id=sid)
            assert result == '{"final_answer": "42"}'

    def test_chat_error_handling(self):
        class FailingStream(MockLLMProvider):
            def generate_stream(self, system_prompt, user_message):
                raise RuntimeError("stream error")

        llm = FailingStream()
        o = Orchestrator(llm)
        result = o.chat("Hello")
        assert result == ""


class TestOrchestratorSkills:
    def test_register_skill(self, mock_llm_direct):
        from mini_agent import Skill
        o = Orchestrator(mock_llm_direct)
        skill = Skill(name="python", description="Python development")
        o.register_skill(skill)
        assert o.skill_registry.get("python") is skill

    def test_skill_matching(self, mock_llm_direct):
        from mini_agent import Skill
        o = Orchestrator(mock_llm_direct)
        o.register_skill(Skill(name="python", description="Expert Python developer"))
        o.register_skill(Skill(name="rust", description="Systems programming in Rust"))
        matched = o._match_skills("Write a Python script")
        assert len(matched) == 1
        assert matched[0].name == "python"


class TestOrchestratorPlanEdgeCases:
    def test_plan_with_hallucinated_skill(self):
        llm = MockLLMProvider(responses=[
            json.dumps({
                "needs_sub_agents": True,
                "sub_tasks": [
                    {
                        "role": "worker",
                        "instructions": "do work",
                        "required_capabilities": [],
                        "skill": "nonexistent",
                        "depends_on": [],
                        "memory": False,
                    },
                ],
            }),
            '{"final_answer": "done"}',
            '{"final_answer": "aggregated"}',
        ])
        import warnings
        o = Orchestrator(llm)
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            plan = o._plan("do work")
            assert any("unknown skill" in str(x.message).lower() for x in w)

    def test_plan_empty_response(self):
        llm = MockLLMProvider(responses=[""])
        o = Orchestrator(llm)
        result = o.run("Hello")
        assert "final_answer" in result

    def test_plan_non_json_response(self):
        llm = MockLLMProvider(responses=["Just a plain text response"])
        o = Orchestrator(llm)
        result = o.run("Hello")
        assert "final_answer" in result


class TestOrchestratorAggregation:
    def test_aggregate_empty_results(self):
        o = Orchestrator(MockLLMProvider())
        result = o._aggregate("Test", {})
        assert result == "No results to aggregate."

    def test_aggregate_single_result(self):
        llm = MockLLMProvider(responses=['synthesized answer'])
        o = Orchestrator(llm)
        result = o._aggregate("Test", {
            "agent_1": {"response": "result 1", "tool_calls": []}
        })
        assert result == "synthesized answer"
