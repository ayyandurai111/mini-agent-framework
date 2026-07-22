"""Tests for ActionTracker."""
from mini_agent.core.utils.action_tracker import ActionTracker, console_event_logger


class TestActionTracker:
    def test_emit_plan_event(self):
        events = []
        def collector(event_type, data):
            events.append((event_type, data))
        tracker = ActionTracker(on_event=collector)
        tracker.on_plan("test task", True, [{"role": "a", "instructions": "do it", "required_capabilities": [], "depends_on": []}])
        assert len(events) == 1
        assert events[0][0] == "plan"
        assert events[0][1]["task"] == "test task"
        assert events[0][1]["needs_sub_agents"] is True

    def test_emit_agent_start(self):
        events = []
        def collector(event_type, data):
            events.append((event_type, data))
        tracker = ActionTracker(on_event=collector)
        tracker.on_agent_start("agent_1", "worker", "do work", capabilities=["web_search"])
        assert len(events) == 1
        assert events[0][0] == "agent_start"
        assert events[0][1]["agent_id"] == "agent_1"

    def test_emit_agent_end(self):
        events = []
        def collector(event_type, data):
            events.append((event_type, data))
        tracker = ActionTracker(on_event=collector)
        tracker.on_agent_end("agent_1", "worker", "task complete")
        assert events[0][0] == "agent_end"

    def test_emit_tool_call(self):
        events = []
        def collector(event_type, data):
            events.append((event_type, data))
        tracker = ActionTracker(on_event=collector)
        tracker.on_tool_call("agent_1", "web_search", {"q": "test"}, iteration=1, total=5)
        assert events[0][0] == "tool_call"
        assert events[0][1]["tool"] == "web_search"

    def test_emit_tool_result(self):
        events = []
        def collector(event_type, data):
            events.append((event_type, data))
        tracker = ActionTracker(on_event=collector)
        tracker.on_tool_result("agent_1", "web_search", "mock result")
        assert events[0][0] == "tool_result"

    def test_emit_aggregate(self):
        events = []
        def collector(event_type, data):
            events.append((event_type, data))
        tracker = ActionTracker(on_event=collector)
        tracker.on_aggregate("test task")
        assert events[0][0] == "aggregate"

    def test_emit_token(self):
        events = []
        def collector(event_type, data):
            events.append((event_type, data))
        tracker = ActionTracker(on_event=collector)
        tracker.on_token("hello", agent_id="chat")
        assert events[0][0] == "token"

    def test_emit_agent_phase(self):
        events = []
        def collector(event_type, data):
            events.append((event_type, data))
        tracker = ActionTracker(on_event=collector)
        tracker.on_agent_phase("agent_1", "researching")
        assert events[0][0] == "agent_phase"

    def test_no_callback_does_not_crash(self):
        tracker = ActionTracker()
        tracker.on_plan("test", False, [])
        tracker.on_agent_start("a", "b", "c")
        tracker.on_agent_end("a", "b", "c")

    def test_console_event_logger_does_not_crash(self):
        tracker = ActionTracker(on_event=console_event_logger)
        tracker.on_plan("test task", True, [{"role": "a", "instructions": "do it", "required_capabilities": [], "depends_on": [0]}])
        tracker.on_agent_start("agent_1", "worker", "do the work", capabilities=["web_search"], skills=["python"])
        tracker.on_tool_call("agent_1", "web_search", {"q": "test"}, iteration=1, total=5)
        tracker.on_tool_result("agent_1", "web_search", "result")
        tracker.on_agent_end("agent_1", "worker", "completed")
        tracker.on_aggregate("test task")
