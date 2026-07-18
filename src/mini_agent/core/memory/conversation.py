import json
import os
from typing import Callable, List, Optional

from ...config.settings import (
    MEMORY_MAX_TURNS,
    MEMORY_CONTEXT_TURNS,
    MEMORY_PERSIST_FILE,
    MAX_CONTEXT_TOKENS,
    SUMMARIZE_EVERY_N_TURNS,
)


class ConversationMemory:
    def __init__(self, max_turns: int = MEMORY_MAX_TURNS,
                 persist_file: str = MEMORY_PERSIST_FILE,
                 summarize_callback: Optional[Callable] = None):
        self._turns: List[str] = self._load(persist_file)
        self._max_turns = max_turns
        self._persist_file = persist_file
        self._summarize_callback = summarize_callback
        self._turn_counter = len(self._turns)

    def add_turn(self, user_input: str, plan: dict, agents: list, result: str):
        formatted = self._format(user_input, plan, agents, result)
        self._turns.append(formatted)
        self._turn_counter += 1
        if self._max_turns > 0:
            while len(self._turns) > self._max_turns:
                self._turns.pop(0)
        self._save()
        if self._summarize_callback and self._turn_counter % SUMMARIZE_EVERY_N_TURNS == 0:
            self._summarize_callback(self)

    def get_context(self) -> str:
        return self._build_compressed_context()

    def _build_compressed_context(self) -> str:
        """Build context with rules + summary + recent turns, respecting token budget."""
        parts = []
        token_count = 0
        budget = MAX_CONTEXT_TOKENS

        # 1. Rules (highest priority)
        if hasattr(self, '_rules_text') and self._rules_text:
            block = f"=== USER RULES ===\n{self._rules_text}\n"
            parts.append(block)
            token_count += self._count_tokens(block)

        # 2. Latest summary
        if hasattr(self, '_summary_text') and self._summary_text:
            block = f"=== CONTEXT SUMMARY ===\n{self._summary_text}\n"
            remaining = budget - token_count
            block_tokens = self._count_tokens(block)
            if block_tokens <= remaining:
                parts.append(block)
                token_count += block_tokens

        # 3. Recent turns (fill remaining budget, newest first)
        remaining = budget - token_count
        recent_blocks = []
        for turn in reversed(self._turns):
            turn_tokens = self._count_tokens(turn)
            if turn_tokens <= remaining:
                recent_blocks.insert(0, turn)
                remaining -= turn_tokens
            else:
                break
            if len(recent_blocks) >= MEMORY_CONTEXT_TURNS:
                break

        if recent_blocks:
            parts.append("\n\n".join(recent_blocks))

        return "\n\n".join(parts)

    def inject_long_term(self, rules_text: str = "", summary_text: str = "") -> None:
        self._rules_text = rules_text
        self._summary_text = summary_text

    # ------------------------------------------------------------------
    # Token counting
    # ------------------------------------------------------------------

    def _count_tokens(self, text: str) -> int:
        try:
            import tiktoken
            enc = tiktoken.get_encoding("cl100k_base")
            return len(enc.encode(text))
        except Exception:
            return len(text) // 4

    def count_tokens_in_turns(self) -> List[int]:
        return [self._count_tokens(t) for t in self._turns]

    def total_tokens(self) -> int:
        return sum(self.count_tokens_in_turns())

    # ------------------------------------------------------------------
    # Search
    # ------------------------------------------------------------------

    def search(self, query: str) -> List[dict]:
        q = query.lower()
        results = []
        for i, turn in enumerate(self._turns):
            if q in turn.lower():
                lines = turn.split("\n")[:5]
                snippet = " | ".join(l.strip() for l in lines if l.strip())[:300]
                results.append({"turn_index": i, "snippet": snippet})
        return results

    # ------------------------------------------------------------------
    # Summarization trigger
    # ------------------------------------------------------------------

    def set_summarize_callback(self, callback: Optional[Callable]) -> None:
        self._summarize_callback = callback

    def get_turns_for_summary(self, start: int, end: int) -> List[str]:
        return list(self._turns[start:end])

    def remove_turns_range(self, start: int, end: int) -> None:
        del self._turns[start:end]
        self._save()

    # ------------------------------------------------------------------
    # Formatting
    # ------------------------------------------------------------------

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

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

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
        self._turn_counter = 0
        self._save()
