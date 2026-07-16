"""Test mini_agent framework — no custom tools/skills"""
import os
from mini_agent import Orchestrator
from mini_agent.core import auto_approve_callback
from mini_agent.providers.nvidia_provider import NvidiaProvider
from mini_agent.registry.builtin import FILE_TOOLS, WEB_TOOLS, MATH_TOOLS, DATA_TOOLS, SYSTEM_TOOLS, BASH_TOOL, BROWSER_TOOLS

llm = NvidiaProvider(api_key=os.environ["NVIDIA_API_KEY"])

o = Orchestrator(llm, approval_callback=auto_approve_callback)
o.register_tools(FILE_TOOLS + WEB_TOOLS + MATH_TOOLS + DATA_TOOLS + SYSTEM_TOOLS + BASH_TOOL + BROWSER_TOOLS)

while True:
    q = input("> ").strip()
    if q.lower() in ("exit", "quit"):
        break
    if q:
        r = o.run(q)
        print(f"  {r.get('final_answer', '')}\n")
