"""
registry/builtin/
-------------------
Ready-made tools organized by category. Import BUILTIN_TOOLS for the safe
defaults, or import individual category lists to register only what you
need.

Usage:
    from mini_agent.registry.builtin import BUILTIN_TOOLS
    orchestrator.register_tools(BUILTIN_TOOLS)

    # or, category by category:
    from mini_agent.registry.builtin import FILE_TOOLS, WEB_TOOLS
    orchestrator.register_tools(FILE_TOOLS)

NOTE: BROWSER_TOOLS (real browser automation via Playwright) is kept
out of BUILTIN_TOOLS â€” install with `pip install mini_agent[browser]`.
Chromium is auto-downloaded on first use if missing.

    from mini_agent.registry.builtin import BROWSER_TOOLS
    orchestrator.register_tools(BROWSER_TOOLS)
"""

from .file_tools import FILE_TOOLS
from .web_tools import WEB_TOOLS
from .data_tools import DATA_TOOLS
from .math_tools import MATH_TOOLS
from .system_tools import SYSTEM_TOOLS
from .bash_tool import BASH_TOOL

def _get_browser_tools():
    from .browser_tools import BROWSER_TOOLS
    return BROWSER_TOOLS

BUILTIN_TOOLS = FILE_TOOLS + WEB_TOOLS + DATA_TOOLS + MATH_TOOLS + SYSTEM_TOOLS + BASH_TOOL


def __getattr__(name):
    if name == "ALL_TOOLS":
        return BUILTIN_TOOLS + _get_browser_tools()
    if name == "BROWSER_TOOLS":
        return _get_browser_tools()
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

__all__ = [
    "BUILTIN_TOOLS",
    "ALL_TOOLS",
    "FILE_TOOLS",
    "WEB_TOOLS",
    "DATA_TOOLS",
    "MATH_TOOLS",
    "SYSTEM_TOOLS",
    "BASH_TOOL",
    "BROWSER_TOOLS",
]
