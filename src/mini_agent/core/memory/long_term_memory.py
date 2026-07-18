import json
import os
from datetime import datetime
from typing import Any, Dict, List, Optional


class LongTermMemory:
    """Persistent long-term memory for a session: summaries of past turns
    and extracted user rules/preferences."""

    def __init__(self, persist_file: str):
        self._persist_file = persist_file
        self._summaries: List[Dict[str, Any]] = []
        self._rules: List[Dict[str, Any]] = []
        self._load()

    # ------------------------------------------------------------------
    # Summaries
    # ------------------------------------------------------------------

    def add_summary(self, turn_range: List[int], summary: str) -> None:
        self._summaries.append({
            "turn_range": turn_range,
            "summary": summary,
            "timestamp": datetime.now().isoformat(),
        })
        self._save()

    def get_latest_summary(self) -> Optional[str]:
        if not self._summaries:
            return None
        return self._summaries[-1]["summary"]

    def get_all_summaries(self) -> List[Dict[str, Any]]:
        return list(self._summaries)

    # ------------------------------------------------------------------
    # Rules
    # ------------------------------------------------------------------

    def add_rules(self, new_rules: List[Dict[str, str]], source_turn: int) -> None:
        for rule in new_rules:
            text = rule.get("rule", "").strip()
            if not text:
                continue
            if not self._has_rule(text):
                self._rules.append({
                    "rule": text,
                    "category": rule.get("category", "general"),
                    "source_turn": source_turn,
                    "timestamp": datetime.now().isoformat(),
                })
        self._save()

    def get_rules(self) -> List[Dict[str, Any]]:
        return list(self._rules)

    def get_rules_text(self) -> str:
        if not self._rules:
            return ""
        blocks = []
        for r in self._rules:
            blocks.append(f"{r['rule']}")
        return "\n".join(blocks)

    def _has_rule(self, text: str) -> bool:
        text_lower = text.lower()
        for r in self._rules:
            if text_lower in r["rule"].lower() or r["rule"].lower() in text_lower:
                return True
        return False

    # ------------------------------------------------------------------
    # Search
    # ------------------------------------------------------------------

    def search_summaries(self, query: str) -> List[Dict[str, Any]]:
        q = query.lower()
        matches = []
        for s in self._summaries:
            if q in s["summary"].lower():
                matches.append(s)
        return matches

    def search_rules(self, query: str) -> List[Dict[str, Any]]:
        q = query.lower()
        matches = []
        for r in self._rules:
            if q in r["rule"].lower():
                matches.append(r)
        return matches

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def _load(self) -> None:
        try:
            with open(self._persist_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            self._summaries = data.get("summaries", [])
            self._rules = data.get("rules", [])
        except (FileNotFoundError, json.JSONDecodeError):
            self._summaries = []
            self._rules = []

    def _save(self) -> None:
        try:
            os.makedirs(os.path.dirname(self._persist_file), exist_ok=True)
            with open(self._persist_file, "w", encoding="utf-8") as f:
                json.dump({
                    "summaries": self._summaries,
                    "rules": self._rules,
                }, f, ensure_ascii=False, indent=2)
        except (OSError, PermissionError, IOError):
            pass
