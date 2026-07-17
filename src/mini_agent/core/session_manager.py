import json
import os
import uuid
from datetime import datetime
from typing import Optional

from ..config.settings import SESSION_MAX_TURNS, get_default_memory_dir
from .memory.conversation import ConversationMemory


class SessionManager:
    """Manages multiple named chat sessions with persistent storage.

    Each session has a unique ID, a user-friendly name, and its own
    ConversationMemory persisted as ``{session_id}.json`` in the sessions
    directory.  An ``index.json`` manifest tracks metadata for all sessions.
    """

    def __init__(self, sessions_dir: Optional[str] = None):
        self.sessions_dir = sessions_dir or get_default_memory_dir()
        self._index_file = os.path.join(self.sessions_dir, "index.json")
        self._cache: dict[str, ConversationMemory] = {}
        self._index = self._load_index()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def create_session(self, name: Optional[str] = None) -> dict:
        """Create a new session and return its metadata dict."""
        session_id = uuid.uuid4().hex
        now = datetime.now().isoformat()
        sessions = self._index["sessions"]
        info = {
            "id": session_id,
            "name": name or f"Session {len(sessions) + 1}",
            "created_at": now,
            "updated_at": now,
            "turn_count": 0,
        }
        sessions[session_id] = info
        self._index["active"] = session_id
        self._save_index()
        session_file = self._session_path(session_id)
        self._cache[session_id] = ConversationMemory(
            persist_file=session_file, max_turns=SESSION_MAX_TURNS
        )
        return dict(info)

    def list_sessions(self) -> list[dict]:
        """Return metadata for every session (turn counts are live)."""
        result = []
        for sid, info in self._index["sessions"].items():
            info["turn_count"] = len(self.get_session(sid).raw_turns())
            result.append(dict(info))
        return result

    def get_session(self, session_id: str) -> ConversationMemory:
        """Return the ConversationMemory for a session (loaded on demand)."""
        if session_id not in self._index["sessions"]:
            raise ValueError(f"Session '{session_id}' not found")
        if session_id not in self._cache:
            session_file = self._session_path(session_id)
            self._cache[session_id] = ConversationMemory(
                persist_file=session_file, max_turns=SESSION_MAX_TURNS
            )
        return self._cache[session_id]

    def delete_session(self, session_id: str):
        """Permanently remove a session (file + index entry)."""
        if session_id not in self._index["sessions"]:
            return
        del self._index["sessions"][session_id]
        self._cache.pop(session_id, None)
        session_file = self._session_path(session_id)
        if os.path.exists(session_file):
            os.remove(session_file)
        if self._index.get("active") == session_id:
            remaining = list(self._index["sessions"].keys())
            self._index["active"] = remaining[0] if remaining else None
        self._save_index()

    def rename_session(self, session_id: str, name: str):
        """Change the display name of a session."""
        if session_id not in self._index["sessions"]:
            raise ValueError(f"Session '{session_id}' not found")
        self._index["sessions"][session_id]["name"] = name
        self._save_index()

    def get_or_create_active(self) -> tuple[str, ConversationMemory]:
        """Return the active session (create one if none exists)."""
        active_id = self._index.get("active")
        if active_id and active_id in self._index["sessions"]:
            return active_id, self.get_session(active_id)
        info = self.create_session()
        return info["id"], self._cache[info["id"]]

    def touch_session(self, session_id: str):
        """Update turn count and timestamp for a session in the index."""
        if session_id in self._index["sessions"]:
            memory = self.get_session(session_id)
            info = self._index["sessions"][session_id]
            info["turn_count"] = len(memory.raw_turns())
            info["updated_at"] = datetime.now().isoformat()
            self._save_index()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _session_path(self, session_id: str) -> str:
        return os.path.join(self.sessions_dir, f"{session_id}.json")

    def _load_index(self) -> dict:
        try:
            os.makedirs(self.sessions_dir, exist_ok=True)
            with open(self._index_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return {"sessions": {}, "active": None}

    def _save_index(self):
        os.makedirs(self.sessions_dir, exist_ok=True)
        with open(self._index_file, "w", encoding="utf-8") as f:
            json.dump(self._index, f, ensure_ascii=False, indent=2)
