"""Tests for built-in tool categories."""
import os
import tempfile
import pytest

from mini_agent.registry.builtin import BUILTIN_TOOLS
from mini_agent.registry.builtin.file_tools import FILE_TOOLS
from mini_agent.registry.builtin.web_tools import WEB_TOOLS
from mini_agent.registry.builtin.math_tools import MATH_TOOLS
from mini_agent.registry.builtin.data_tools import DATA_TOOLS
from mini_agent.registry.builtin.system_tools import SYSTEM_TOOLS


class TestFileTools:
    def test_read_text_file(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False, encoding="utf-8") as f:
            f.write("hello world")
            path = f.name
        try:
            tool = next(t for t in FILE_TOOLS if t.name == "read_text_file")
            result = tool.run(path=path)
            assert "hello world" in result
        finally:
            os.unlink(path)

    def test_write_file(self):
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "test.txt")
            tool = next(t for t in FILE_TOOLS if t.name == "write_text_file")
            result = tool.run(path=path, content="test content")
            assert "test content" in result or "Wrote" in str(result)
            assert os.path.exists(path)

    def test_file_exists_true(self):
        with tempfile.NamedTemporaryFile(mode="w", delete=False) as f:
            path = f.name
        try:
            tool = next(t for t in FILE_TOOLS if t.name == "file_exists")
            result = tool.run(path=path)
            assert result == "true"
        finally:
            os.unlink(path)

    def test_file_exists_false(self):
        tool = next(t for t in FILE_TOOLS if t.name == "file_exists")
        result = tool.run(path="C:\\nonexistent_file_xyz_test.txt")
        assert result == "false"

    def test_list_directory(self):
        with tempfile.TemporaryDirectory() as d:
            open(os.path.join(d, "a.txt"), "w").close()
            open(os.path.join(d, "b.txt"), "w").close()
            tool = next(t for t in FILE_TOOLS if t.name == "list_directory")
            result = tool.run(path=d)
            assert "a.txt" in result
            assert "b.txt" in result

    def test_append_file(self):
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "test.txt")
            with open(path, "w") as f:
                f.write("original")
            tool = next(t for t in FILE_TOOLS if t.name == "append_text_file")
            result = tool.run(path=path, content=" appended")
            assert "Appended" in result


class TestMathTools:
    def test_calculator(self):
        tool = next(t for t in MATH_TOOLS if t.name == "calculator")
        result = tool.run(expression="2+2")
        assert "4" in str(result)

    def test_calculator_complex(self):
        tool = next(t for t in MATH_TOOLS if t.name == "calculator")
        result = tool.run(expression="3 * 4 + 2")
        assert "14" in str(result)

    def test_calculator_error(self):
        tool = next(t for t in MATH_TOOLS if t.name == "calculator")
        result = tool.run(expression="1/0")
        assert "Error" in str(result) or "zero" in str(result).lower()

    def test_generate_uuid(self):
        tool = next(t for t in MATH_TOOLS if t.name == "generate_uuid")
        result = tool.run()
        assert len(result) == 36

    def test_word_count(self):
        tool = next(t for t in MATH_TOOLS if t.name == "word_count")
        result = tool.run(text="hello world")
        assert result == "2"

    def test_random_number(self):
        tool = next(t for t in MATH_TOOLS if t.name == "random_number")
        result = tool.run(min_value=1, max_value=10)
        assert 1 <= int(result) <= 10


class TestSystemTools:
    def test_datetime(self):
        tool = next(t for t in SYSTEM_TOOLS if t.name == "get_current_datetime")
        result = tool.run()
        assert "202" in str(result)

    def test_cwd(self):
        tool = next(t for t in SYSTEM_TOOLS if t.name == "get_current_working_directory")
        result = tool.run()
        assert result is not None


class TestDataTools:
    def test_read_json_valid(self):
        import json
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False, encoding="utf-8") as f:
            json.dump({"key": "value"}, f)
            path = f.name
        try:
            tool = next(t for t in DATA_TOOLS if t.name == "read_json")
            result = tool.run(path=path)
            assert "key" in str(result)
        finally:
            os.unlink(path)


class TestBuiltinToolsComposition:
    def test_builtin_tools_contains_all_categories(self):
        names = [t.name for t in BUILTIN_TOOLS]
        assert "read_text_file" in names
        assert "web_search" in names
        assert "calculator" in names
        assert "generate_uuid" in names
        assert "get_current_datetime" in names
        assert "read_json" in names

    def test_no_duplicate_names(self):
        names = [t.name for t in BUILTIN_TOOLS]
        assert len(names) == len(set(names))

    def test_all_tools_have_descriptions(self):
        for t in BUILTIN_TOOLS:
            assert t.description

    def test_all_tools_have_parameters(self):
        for t in BUILTIN_TOOLS:
            assert t.parameters is not None
