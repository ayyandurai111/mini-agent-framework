"""
core/action_tracker.py
-----------------------
ActionTracker — live-action callback system for the framework.
Emits events for planning, agent start/end, and tool calls with results.
Framework users can attach custom callbacks, or use the default console logger.
"""

import sys
from typing import Callable, Optional


class ActionTracker:
    def __init__(self, on_event: Optional[Callable[[str, dict], None]] = None):
        self._custom_callback = on_event

    def emit(self, event_type: str, data: dict):
        if self._custom_callback:
            self._custom_callback(event_type, data)

    def on_plan(self, task: str, needs_sub_agents: bool, sub_tasks: list,
                tools_count: int = 0, skills_available: list = None,
                required_capabilities: list = None):
        self.emit("plan", {
            "task": task,
            "needs_sub_agents": needs_sub_agents,
            "sub_tasks": sub_tasks,
            "tools_count": tools_count,
            "skills_available": skills_available or [],
            "required_capabilities": required_capabilities or [],
        })

    def on_research(self, tool: str, arguments: dict, result: str):
        self.emit("research", {"tool": tool, "arguments": arguments, "result": result})

    def on_agent_start(self, agent_id: str, role: str, instructions: str,
                       capabilities: list = None, skills: list = None):
        self.emit("agent_start", {
            "agent_id": agent_id,
            "role": role,
            "instructions": instructions,
            "capabilities": capabilities or [],
            "skills": skills or [],
        })

    def on_agent_phase(self, agent_id: str, phase: str):
        self.emit("agent_phase", {"agent_id": agent_id, "phase": phase})

    def on_agent_end(self, agent_id: str, role: str, result: str):
        self.emit("agent_end", {"agent_id": agent_id, "role": role, "result": result})

    def on_tool_call(self, agent_id: str, tool: str, arguments: dict, iteration: int = 0, total: int = 0):
        self.emit("tool_call", {
            "agent_id": agent_id,
            "tool": tool,
            "arguments": arguments,
            "iteration": iteration,
            "total": total,
        })

    def on_tool_result(self, agent_id: str, tool: str, result: str):
        self.emit("tool_result", {"agent_id": agent_id, "tool": tool, "result": result})

    def on_aggregate(self, task: str):
        self.emit("aggregate", {"task": task})


def console_event_logger(event_type: str, data: dict):
    """Readable event logger with box-drawing and indentation."""
    aid = data.get("agent_id", "")

    if event_type == "plan":
        needs = "single-agent" if not data["needs_sub_agents"] else "multi-agent"
        sub_count = len(data.get("sub_tasks", []))
        tools_count = data.get("tools_count", 0)
        skills = data.get("skills_available", [])

        print("\n\u2554\u2550\u2550\u2550 PLAN \u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550", file=sys.stderr)
        print(f"\u2551  Decision : {needs}{f' ({sub_count} sub-tasks)' if sub_count else ''}", file=sys.stderr)
        if data.get("sub_tasks"):
            for i, t in enumerate(data["sub_tasks"]):
                caps = t.get("required_capabilities", [])
                deps = t.get("depends_on", [])
                dep_str = f"  \u2190 after #{', #'.join(str(d) for d in deps)}" if deps else ""
                print(f"\u2551  Task #{i} : {t.get('role', '?')}  [{', '.join(caps)}]{dep_str}", file=sys.stderr)
        else:
            caps = data.get("required_capabilities", [])
            if caps:
                print(f"\u2551  Tools : {', '.join(caps)}", file=sys.stderr)
            if skills:
                print(f"\u2551  Skills: {', '.join(skills)}", file=sys.stderr)
        print("\u255a\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550", file=sys.stderr)

    elif event_type == "agent_start":
        role = data["role"]
        caps = data.get("capabilities", [])
        skills = data.get("skills", [])
        task_preview = data.get("instructions", "")[:90]

        print(f"\n    \u250c\u2550\u2550 WORKER: {role} \u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2510", file=sys.stderr)
        if task_preview:
            print(f"    \u2502  {task_preview}", file=sys.stderr)
        if caps:
            print(f"    \u2502  Tools: {', '.join(caps)}", file=sys.stderr)
        if skills:
            print(f"    \u2502  Skills: {', '.join(skills)}", file=sys.stderr)

    elif event_type == "tool_call":
        tool = data["tool"]
        args = data["arguments"]
        iteration = data.get("iteration", 0)
        total = data.get("total", 0)
        arg_str = ", ".join(f"{k}={v}" for k, v in args.items())
        if aid == "planner":
            print(f"  \u250f  {tool}({arg_str})", file=sys.stderr)
        else:
            progress = f"{iteration}/{total}" if total else ""
            print(f"    \u2502  {progress}  \u2699 {tool}({arg_str})", file=sys.stderr)

    elif event_type == "tool_result":
        result = str(data.get("result", ""))[:150].replace("\n", " ")
        if aid == "planner":
            print(f"  \u2503  \u2192 {result}", file=sys.stderr)
        else:
            print(f"    \u2502        \u2192 {result}", file=sys.stderr)

    elif event_type == "agent_end":
        result_preview = str(data.get("result", ""))[:100].replace("\n", " ")
        print(f"    \u2502  \u2705 {result_preview}", file=sys.stderr)
        print(f"    \u2514\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2518", file=sys.stderr)

    elif event_type == "aggregate":
        print(f"\n\u2554\u2550\u2550\u2550 AGGREGATOR \u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550", file=sys.stderr)
        print(f"\u2551  Merging agent outputs...", file=sys.stderr)
        print(f"\u255a\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550", file=sys.stderr)
