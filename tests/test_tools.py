"""Tests for Tool dataclass and ToolRegistry."""
import pytest
from mini_agent.registry.tools import Tool, ToolRegistry, RegistryError


class TestTool:
    def test_create_tool(self):
        def my_func(x, y):
            return x + y

        t = Tool(name="add", description="Adds two numbers", func=my_func)
        assert t.name == "add"
        assert t.run(1, 2) == 3
        assert t.read_only is True
        assert t.requires_approval is False

    def test_tool_auto_detect_parameters(self):
        def greet(name: str, greeting: str = "Hello"):
            return f"{greeting}, {name}"

        t = Tool(name="greet", description="Greets someone", func=greet)
        assert "name" in t.parameters
        assert "greeting" in t.parameters

    def test_tool_empty_name_raises(self):
        with pytest.raises(ValueError, match="name"):
            Tool(name="", description="test", func=lambda: None)

    def test_tool_empty_description_raises(self):
        with pytest.raises(ValueError, match="description"):
            Tool(name="test", description="", func=lambda: None)

    def test_tool_run_with_validator(self):
        def only_positive(x):
            return x

        def validate_positive(x):
            return x > 0

        t = Tool(name="positive", description="Only positives", func=only_positive, validator=validate_positive)
        assert t.run(5) == 5
        with pytest.raises(ValueError, match="Validation failed"):
            t.run(-1)

    def test_tool_on_error_callback(self):
        def failing():
            raise ValueError("boom")

        def handler(e):
            return f"handled: {e}"

        t = Tool(name="safe", description="Safe tool", func=failing, on_error=handler)
        assert t.run() == "handled: boom"

    def test_tool_describe(self):
        t = Tool(name="my_tool", description="Does something", func=lambda x: x)
        desc = t.describe()
        assert "my_tool" in desc
        assert "Does something" in desc

    def test_tool_requires_approval_flag(self):
        t = Tool(name="danger", description="Dangerous", func=lambda: None, requires_approval=True)
        assert t.requires_approval is True

    def test_tool_read_only_flag(self):
        t_write = Tool(name="write", description="Write tool", func=lambda: None, read_only=False)
        assert t_write.read_only is False


class TestToolRegistry:
    def test_register_and_get(self):
        reg = ToolRegistry()
        t = Tool(name="test", description="Test tool", func=lambda: None)
        reg.register(t)
        assert reg.get("test") is t

    def test_register_duplicate_warns(self):
        reg = ToolRegistry()
        t1 = Tool(name="dup", description="First", func=lambda: None)
        t2 = Tool(name="dup", description="Second", func=lambda: None)
        reg.register(t1)
        import warnings
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            reg.register(t2)
            assert len(w) == 1
            assert "already registered" in str(w[0].message)

    def test_unregister(self):
        reg = ToolRegistry()
        t = Tool(name="test", description="Test", func=lambda: None)
        reg.register(t)
        reg.unregister("test")
        assert reg.get("test") is None

    def test_match(self):
        reg = ToolRegistry()
        t1 = Tool(name="a", description="A", func=lambda: None)
        t2 = Tool(name="b", description="B", func=lambda: None)
        reg.register(t1)
        reg.register(t2)
        matched = reg.match(["a", "c"])
        assert len(matched) == 1
        assert matched[0] is t1

    def test_list_available(self):
        reg = ToolRegistry()
        t1 = Tool(name="a", description="A", func=lambda: None)
        t2 = Tool(name="b", description="B", func=lambda: None)
        reg.register(t1)
        reg.register(t2)
        assert set(reg.list_available()) == {"a", "b"}

    def test_get_read_only(self):
        reg = ToolRegistry()
        ro = Tool(name="ro", description="Read only", func=lambda: None, read_only=True)
        rw = Tool(name="rw", description="Read write", func=lambda: None, read_only=False)
        reg.register(ro)
        reg.register(rw)
        assert reg.get_read_only() == ["ro"]

    def test_register_empty_name_raises(self):
        reg = ToolRegistry()
        with pytest.raises(RegistryError, match="name"):
            t = Tool(name="test", description="valid", func=lambda: None)
            t.name = ""
            reg.register(t)

    def test_register_empty_description_raises(self):
        reg = ToolRegistry()
        with pytest.raises(RegistryError, match="description"):
            t = Tool(name="test", description="valid", func=lambda: None)
            t.description = ""
            reg.register(t)
