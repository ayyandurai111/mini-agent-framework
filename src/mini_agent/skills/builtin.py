"""
skills/builtin.py
--------------------
Pre-defined skills bundled with the framework.
Import directly and register like built-in tools:

    from mini_agent.skills import CODE_REVIEW, DEVELOPER, SKILLS

    orch.register_skills(SKILLS)                          # all bundled
    orch.register_skills(CODE_REVIEW + DEVELOPER)          # select few
"""

from . import discover_package_skills

_all = discover_package_skills()

SKILLS = _all

# ── Individual skill lists (one per skill directory) ──
CODE_REVIEW = [s for s in _all if s.name == "code-review"]
DEVELOPER   = [s for s in _all if s.name == "developer"]
SYSTEM_DESIGN_PLANNING = [s for s in _all if s.name == "system-design-planning"]

__all__ = [
    "SKILLS",
    "CODE_REVIEW",
    "DEVELOPER",
    "SYSTEM_DESIGN_PLANNING",
]
