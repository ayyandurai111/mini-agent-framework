"""
Big example: Build a full calculator project using mini-agent-framework.
Demonstrates: tool registration, skill injection, multi-file writing, rate-limit resilience.
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from mini_agent import Orchestrator, NvidiaProvider
from mini_agent.registry.builtin import BUILTIN_TOOLS
from mini_agent.skills.builtin import SKILLS

API_KEY = os.environ.get("NVIDIA_API_KEY")
if not API_KEY:
    raise SystemExit("Set NVIDIA_API_KEY environment first")

orch = Orchestrator(
    NvidiaProvider(api_key=API_KEY, max_retries=5),
    max_agents=2,
)

orch.register_tools(BUILTIN_TOOLS)
orch.register_skills(SKILLS)

TASK = """
Build a Python calculator project with these files:
  1. calculator_ops.py — math operations (add, sub, mul, div, pow, mod)
  2. calculator_ui.py — terminal UI with input loop
  3. calculator_test.py — pytest tests for all operations
  4. main.py — entry point that imports and runs the UI

Write all files to F:\calculator_demo\ using write_text_file tool.
"""

print(f"\n{'='*60}")
print("Starting calculator project build...")
print(f"{'='*60}")

result = orch.run(TASK)

print(f"\n{'='*60}")
print("RESULT")
print(f"{'='*60}")
print(result.get("final_answer", "No response"))
