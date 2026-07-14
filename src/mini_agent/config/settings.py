"""
config/settings.py
--------------------
Framework-wide limits, centralized here for cost/loop control.
"""

# Max number of sub-agents that can be spawned for a single task
MAX_AGENTS = 5

# Max recursion depth for recursive sub-agent spawning
MAX_RECURSION_DEPTH = 2

# Max tool-call round trips a single agent can make before being forced
# to give a final answer (prevents infinite tool-calling loops)
MAX_TOOL_ITERATIONS = 5

# Max number of summarized conversations retained in memory.
# Only the last N are passed to the main agent for context.
MEMORY_MAX_STORED_ENTRIES = 5

# Token budget per single conversation summary.
MEMORY_SUMMARY_MAX_TOKENS = 100

# File path for persistent session memory.
# Summaries survive shutdown â€“ loaded into RAM on startup, saved on every add.
MEMORY_PERSIST_FILE = ".agent_memory.json"
