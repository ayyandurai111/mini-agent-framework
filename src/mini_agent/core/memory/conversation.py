import json
import os
from typing import List, Optional

from ...config.settings import MEMORY_MAX_TURNS, MEMORY_CONTEXT_TURNS, MEMORY_PERSIST_FILE


class ConversationMemory:
    def __init__(self, max_turns: int = MEMORY_MAX_TURNS,
                 persist_file: str = MEMORY_PERSIST_FILE):
        self._turns: List[str] = self._load(persist_file)
        self._max_turns = max_turns
        self._persist_file = persist_file

    def add_turn(self, user_input: str, plan: dict, agents: list, result: str):
        formatted = self._format(user_input, plan, agents, result)
        self._turns.append(formatted)
        if self._max_turns > 0:
            while len(self._turns) > self._max_turns:
                self._turns.pop(0)
        self._save()

    def get_context(self) -> str:
        count = min(MEMORY_CONTEXT_TURNS, len(self._turns))
        if count == 0:
            return ""
        recent = self._turns[-count:]
        return "\n\n".join(recent)

    def _format(self, user_input: str, plan: dict, agents: list, result: str) -> str:
        lines = []
        lines.append("=== USER ===")
        lines.append(user_input)
        lines.append("")

        needs_sub = plan.get("needs_sub_agents", False)
        sub_tasks = plan.get("sub_tasks", [])
        lines.append("=== PLAN ===")
        if needs_sub and sub_tasks:
            lines.append(f"sub_agents: {len(sub_tasks)}")
            for i, t in enumerate(sub_tasks):
                deps = t.get("depends_on", [])
                dep_str = f" (depends on {', '.join(str(d) for d in deps)})" if deps else ""
                cap_str = ""
                caps = t.get("required_capabilities", [])
                if caps:
                    cap_str = f" [{', '.join(caps)}]"
                lines.append(f"  {i}: {t.get('role', '?')}{cap_str} — {t.get('instructions', '')[:80]}{dep_str}")
        else:
            lines.append("direct_agent")
        lines.append("")

        for agent in agents:
            idx = agent.get("index")
            role = agent.get("role", "?")
            if idx is not None:
                lines.append(f"=== AGENT[{idx}]: {role} ===")
            else:
                lines.append(f"=== AGENT[direct]: {role} ===")

            response = agent.get("response", "")
            lines.append(f"[{response[:200]}]")

            for tc in agent.get("tool_calls", []):
                tool = tc.get("tool", "?")
                args = tc.get("arguments", {})
                arg_str = ", ".join(f"{k}={v}" for k, v in args.items())
                res = str(tc.get("result", ""))[:200].replace("\n", " ")
                lines.append(f"  >> {tool}({arg_str}) -> {res}")

            lines.append("")

        lines.append("=== RESULT ===")
        lines.append(result[:500])
        return "\n".join(lines)

    def _save(self):
        try:
            os.makedirs(os.path.dirname(self._persist_file), exist_ok=True)
            with open(self._persist_file, "w", encoding="utf-8") as f:
                json.dump(self._turns, f, ensure_ascii=False, indent=2)
        except (OSError, PermissionError, IOError):
            pass

    def _load(self, path: str) -> List[str]:
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return []

    def raw_turns(self) -> List[str]:
        return list(self._turns)

    def clear(self):
        self._turns = []
        self._save()
