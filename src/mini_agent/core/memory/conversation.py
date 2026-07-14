"""
core/memory/conversation.py
-------------------------------
ConversationMemory â€” LLM-summarizes every agent conversation before storing.
Only the last N summarized entries are kept. Persisted to a JSON file so
memory survives PC shutdown; loaded into RAM on startup.
"""

import json
import os
from typing import List, Optional

from ...llm.base import BaseLLMProvider
from ...config.settings import MEMORY_MAX_STORED_ENTRIES, MEMORY_SUMMARY_MAX_TOKENS, MEMORY_PERSIST_FILE


class ConversationMemory:
    def __init__(self, llm_provider: Optional[BaseLLMProvider] = None,
                 max_stored: int = MEMORY_MAX_STORED_ENTRIES,
                 summary_max_tokens: int = MEMORY_SUMMARY_MAX_TOKENS,
                 persist_file: str = MEMORY_PERSIST_FILE):
        self._summaries: List[str] = self._load(persist_file)
        self._llm_provider = llm_provider
        self._max_stored = max_stored
        self._summary_max_tokens = summary_max_tokens
        self._persist_file = persist_file

    def add_entry(self, role: str, content: str):
        if self._llm_provider is None:
            self._summaries.append(f"[{role}] {content[:200]}")
        else:
            summary = self._summarize(role, content)
            self._summaries.append(summary)
        while len(self._summaries) > self._max_stored:
            self._summaries.pop(0)
        self._save()

    def _summarize(self, role: str, content: str) -> str:
        prompt = (
            f"Summarize the following agent conversation in concise form "
            f"(under {self._summary_max_tokens} tokens). "
            "Preserve key facts, decisions, actions taken, and results. "
            "Strip greetings and filler. Output only the summary â€” no preamble.\n\n"
            f"Agent role: {role}\n"
            f"Content:\n{content[:1200]}"
        )
        try:
            return self._llm_provider.generate(
                system_prompt="You are a conversation summarizer. Be concise.",
                user_message=prompt,
            ).strip()
        except Exception:
            return f"[{role}] {content[:200]}"

    def get_context(self) -> str:
        if not self._summaries:
            return ""
        lines = "\n".join(f"- {s}" for s in self._summaries)
        return (
            f"[Recent agent conversations (last {len(self._summaries)})]\n{lines}"
        )

    def _save(self):
        try:
            with open(self._persist_file, "w", encoding="utf-8") as f:
                json.dump(self._summaries, f, ensure_ascii=False, indent=2)
        except (OSError, PermissionError, IOError):
            pass

    def _load(self, path: str) -> List[str]:
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return []

    def raw_summaries(self) -> List[str]:
        return list(self._summaries)
