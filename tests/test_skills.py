"""Tests for Skill system."""
import os
import tempfile

import pytest
from mini_agent.skills import (
    Skill, SkillRegistry, read_skill_content,
    load_skill_from_file, load_skills_from_dir,
    discover_package_skills, _skill_matches,
)


class TestSkill:
    def test_create_skill(self):
        s = Skill(name="python", description="Python development expertise")
        assert s.name == "python"
        assert s.description == "Python development expertise"
        assert s.file_path == ""

    def test_empty_name_raises(self):
        with pytest.raises(ValueError, match="name"):
            Skill(name="", description="test")

    def test_empty_description_raises(self):
        with pytest.raises(ValueError, match="description"):
            Skill(name="test", description="")

    def test_skill_describe(self):
        s = Skill(name="python", description="Python skills")
        d = s.describe()
        assert "python" in d
        assert "Python skills" in d


class TestSkillRegistry:
    def test_register_and_get(self):
        reg = SkillRegistry()
        s = Skill(name="test", description="Test skill")
        reg.register(s)
        assert reg.get("test") is s

    def test_register_duplicate_warns(self):
        reg = SkillRegistry()
        reg.register(Skill(name="dup", description="First"))
        import warnings
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            reg.register(Skill(name="dup", description="Second"))
            assert any("already registered" in str(x.message) for x in w)

    def test_unregister(self):
        reg = SkillRegistry()
        reg.register(Skill(name="test", description="Test"))
        reg.unregister("test")
        assert reg.get("test") is None

    def test_match(self):
        reg = SkillRegistry()
        reg.register(Skill(name="python", description="Expert Python developer"))
        reg.register(Skill(name="rust", description="Systems programming in Rust"))
        matched = reg.match("I need a Python developer")
        assert len(matched) == 1
        assert matched[0].name == "python"

    def test_match_no_keyword_overlap(self):
        reg = SkillRegistry()
        reg.register(Skill(name="python", description="Expert Python developer"))
        matched = reg.match("I need help with cooking recipes")
        assert len(matched) == 0

    def test_list(self):
        reg = SkillRegistry()
        reg.register(Skill(name="a", description="A"))
        reg.register(Skill(name="b", description="B"))
        assert set(reg.list()) == {"a", "b"}

    def test_empty_name_raises_registry_error(self):
        reg = SkillRegistry()
        with pytest.raises(Exception):
            reg.register(Skill(name="", description="test"))


class TestSkillMatching:
    def test_basic_match(self):
        s = Skill(name="python", description="Expert Python developer skills")
        assert _skill_matches(s, "write python developer code")

    def test_no_match(self):
        s = Skill(name="python", description="Python development")
        assert not _skill_matches(s, "cooking recipes")

    def test_partial_word_match(self):
        s = Skill(name="py", description="py coding")
        assert not _skill_matches(s, "i love py")

    def test_multi_word_match(self):
        s = Skill(name="system-design", description="System architecture and design planning")
        assert _skill_matches(s, "design a system")


class TestSkillFileLoading:
    def test_load_from_file_no_frontmatter(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False, encoding="utf-8") as f:
            f.write("# Python\n\nSome content about Python.")
            path = f.name
        try:
            skill = load_skill_from_file(path)
            assert skill.name == os.path.splitext(os.path.basename(path))[0]
            assert skill.file_path == path
        finally:
            os.unlink(path)

    def test_load_from_file_with_frontmatter(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False, encoding="utf-8") as f:
            f.write("---\nname: python-dev\ndescription: Expert Python development\n---\n\nContent here")
            path = f.name
        try:
            skill = load_skill_from_file(path)
            assert skill.name == "python-dev"
            assert skill.description == "Expert Python development"
        finally:
            os.unlink(path)

    def test_load_from_dir(self):
        with tempfile.TemporaryDirectory() as d:
            skill_dir = os.path.join(d, "python-dev")
            os.makedirs(skill_dir)
            with open(os.path.join(skill_dir, "python-dev.md"), "w", encoding="utf-8") as f:
                f.write("---\nname: python-dev\ndescription: Python skills\n---\n\nContent")
            skills = load_skills_from_dir(d)
            assert len(skills) == 1
            assert skills[0].name == "python-dev"

    def test_load_from_dir_empty(self):
        with tempfile.TemporaryDirectory() as d:
            skills = load_skills_from_dir(d)
            assert len(skills) == 0

    def test_load_from_dir_ignores_non_dirs(self):
        with tempfile.TemporaryDirectory() as d:
            open(os.path.join(d, "file.txt"), "w").close()
            skills = load_skills_from_dir(d)
            assert len(skills) == 0

    def test_read_skill_content(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False, encoding="utf-8") as f:
            f.write("---\nname: test\n---\n\n# Content")
            path = f.name
        try:
            skill = Skill(name="test", description="Test", file_path=path)
            content = read_skill_content(skill)
            assert "Content" in content
        finally:
            os.unlink(path)

    def test_read_skill_content_no_file(self):
        skill = Skill(name="test", description="Fallback description")
        content = read_skill_content(skill)
        assert content == "Fallback description"

    def test_discover_package_skills(self):
        """Should find bundled skills in the package."""
        skills = discover_package_skills()
        assert len(skills) > 0
        names = [s.name for s in skills]
        assert "developer" in names
