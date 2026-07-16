"""
config/settings.py
--------------------
Framework-wide limits, centralized here for cost/loop control.
"""

import os
import platform

# Max number of sub-agents that can be spawned for a single task
MAX_AGENTS = 5

# Max recursion depth for recursive sub-agent spawning
MAX_RECURSION_DEPTH = 2

# Max tool-call round trips a single agent can make before being forced
# to give a final answer (prevents infinite tool-calling loops)
MAX_TOOL_ITERATIONS = 5

# Max number of conversation turns retained in memory.
# Only the last N are passed to the main agent for context.
MEMORY_MAX_TURNS = 5

# Number of recent turns included in the prompt for agent context.
MEMORY_CONTEXT_TURNS = 2


def get_default_memory_dir() -> str:
    """Platform-appropriate directory for session files."""
    system = platform.system()
    if system == "Windows":
        base = os.environ.get("APPDATA", os.path.expanduser("~"))
        return os.path.join(base, "mini_agent", "sessions")
    elif system == "Darwin":
        return os.path.join(os.path.expanduser("~"), "Library",
                            "Application Support", "mini_agent", "sessions")
    else:
        xdg = os.environ.get("XDG_CONFIG_HOME",
                             os.path.join(os.path.expanduser("~"), ".config"))
        return os.path.join(xdg, "mini_agent", "sessions")


def get_default_memory_path(name: str = "session.json") -> str:
    """Full path to a session file, creating the directory if needed."""
    d = get_default_memory_dir()
    os.makedirs(d, exist_ok=True)
    return os.path.join(d, name)


# Default session file path (platform-aware, created lazily).
# Override by passing memory_file to Orchestrator.
MEMORY_PERSIST_FILE = get_default_memory_path()
