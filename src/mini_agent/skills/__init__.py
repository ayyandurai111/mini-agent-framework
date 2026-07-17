"""
skills/__init__.py
--------------------
Skill = reusable domain expertise. Only name + description stored in memory.
Full content is read from the .md file on disk only when matched.

Each skill lives in its own directory: skills/<skill-name>/<skill-name>.md
"""

import os
import re
from dataclasses import dataclass
from typing import List, Optional


@dataclass
class Skill:
    name: str
    description: str
    file_path: str = ""

    def __post_init__(self):
        if not self.name or not self.name.strip():
            raise ValueError("Skill 'name' is required")
        if not self.description:
            raise ValueError(f"Skill '{self.name}' has no description")

    def describe(self) -> str:
        return f"{self.name}: {self.description}"


class RegistryError(Exception):
    pass


class SkillRegistry:
    def __init__(self):
        self._skills: dict[str, Skill] = {}

    def register(self, skill: Skill):
        if not skill.name or not skill.name.strip():
            raise RegistryError("Skill name cannot be empty")
        if not skill.description:
            raise RegistryError(f"Skill '{skill.name}' has no description")
        if skill.name in self._skills:
            import warnings
            warnings.warn(f"Skill '{skill.name}' already registered — overwriting")
        self._skills[skill.name] = skill

    def unregister(self, name: str):
        self._skills.pop(name, None)

    def get(self, name: str) -> Optional[Skill]:
        return self._skills.get(name)

    def match(self, task_text: str) -> List[Skill]:
        matched = []
        task_lower = task_text.lower()
        for skill in self._skills.values():
            if _skill_matches(skill, task_lower):
                matched.append(skill)
        return matched

    def list(self) -> List[str]:
        return list(self._skills.keys())

    def load_from_file(self, path: str) -> Skill:
        return load_skill_from_file(path)

    def load_from_dir(self, directory: str) -> List[Skill]:
        return load_skills_from_dir(directory)


def _skill_matches(skill: Skill, task_lower: str) -> bool:
    desc_lower = skill.description.lower()
    task_words = set(re.findall(r"[a-zA-Z]{3,}", task_lower))
    desc_words = set(re.findall(r"[a-zA-Z]{3,}", desc_lower))
    return bool(task_words & desc_words)


_FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n?(.*)", re.DOTALL)


def _parse_frontmatter(text: str) -> dict:
    text = text.strip()
    if text.startswith("{"):
        import json
        return json.loads(text)
    meta = {}
    for line in text.splitlines():
        line = line.strip()
        m = re.match(r"^([a-zA-Z_]\w*)\s*:\s*(.*)", line)
        if m:
            key = m.group(1)
            val = m.group(2).strip().strip('"').strip("'")
            meta[key] = val
    return meta


def read_skill_content(skill: Skill) -> str:
    """Read the full .md content from disk (frontmatter + body)."""
    if not skill.file_path or not os.path.exists(skill.file_path):
        return skill.description
    with open(skill.file_path, encoding="utf-8") as f:
        return f.read()


def load_skill_from_file(path: str) -> Skill:
    path = os.path.abspath(path)
    with open(path, encoding="utf-8") as f:
        content = f.read()

    m = _FRONTMATTER_RE.match(content)
    if not m:
        name = os.path.splitext(os.path.basename(path))[0]
        return Skill(name=name, description=content.strip()[:200], file_path=path)

    meta = _parse_frontmatter(m.group(1))
    return Skill(
        name=meta.get("name", os.path.splitext(os.path.basename(path))[0]),
        description=meta.get("description", ""),
        file_path=path,
    )


def load_skills_from_dir(directory: str) -> List[Skill]:
    skills = []
    if not os.path.isdir(directory):
        return skills
    for entry in sorted(os.listdir(directory)):
        skill_dir = os.path.join(directory, entry)
        if not os.path.isdir(skill_dir):
            continue
        for fname in os.listdir(skill_dir):
            if fname.endswith(".md"):
                try:
                    skills.append(load_skill_from_file(os.path.join(skill_dir, fname)))
                except Exception:
                    pass
                break
    return skills


_PACKAGE_DIR = os.path.dirname(os.path.abspath(__file__))


def discover_package_skills() -> "List[Skill]":
    """Auto-discover all skill subdirectories inside the skills package dir."""
    """Auto-discover all skill subdirectories inside the skills package dir."""
    skills = []
    for entry in sorted(os.listdir(_PACKAGE_DIR)):
        skill_dir = os.path.join(_PACKAGE_DIR, entry)
        if not os.path.isdir(skill_dir) or entry.startswith("_"):
            continue
        for fname in os.listdir(skill_dir):
            if fname.endswith(".md"):
                try:
                    skills.append(load_skill_from_file(os.path.join(skill_dir, fname)))
                except Exception:
                    pass
                break
    return skills
