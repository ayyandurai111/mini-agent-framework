"""Tests for SessionManager."""
import json
import os
import tempfile

import pytest
from mini_agent.core.session_manager import SessionManager


class TestSessionManager:
    def test_create_session(self):
        with tempfile.TemporaryDirectory() as d:
            sm = SessionManager(sessions_dir=d)
            session = sm.create_session("test_session")
            assert session is not None
            assert sm.get_session(session["id"]) is not None

    def test_get_or_create_active(self):
        with tempfile.TemporaryDirectory() as d:
            sm = SessionManager(sessions_dir=d)
            sid, session = sm.get_or_create_active()
            assert sid is not None
            assert session is not None

    def test_list_sessions(self):
        with tempfile.TemporaryDirectory() as d:
            sm = SessionManager(sessions_dir=d)
            sessions = sm.list_sessions()
            assert isinstance(sessions, list)

    def test_delete_session(self):
        with tempfile.TemporaryDirectory() as d:
            sm = SessionManager(sessions_dir=d)
            info = sm.create_session("to_delete")
            sm.delete_session(info["id"])
            sessions = sm.list_sessions()
            assert all(s["id"] != info["id"] for s in sessions)

    def test_touch_session_updates_timestamp(self):
        with tempfile.TemporaryDirectory() as d:
            sm = SessionManager(sessions_dir=d)
            info = sm.create_session("test")
            sid = info["id"]
            original = sm._index["sessions"][sid]["updated_at"]
            import time
            time.sleep(0.01)
            sm.touch_session(sid)
            updated = sm._index["sessions"][sid]["updated_at"]
            assert updated > original

    def test_create_session_returns_metadata(self):
        with tempfile.TemporaryDirectory() as d:
            sm = SessionManager(sessions_dir=d)
            info = sm.create_session("test")
            assert info["name"] == "test"
            assert "turn_count" in info
            assert "id" in info

    def test_long_term_memory(self):
        with tempfile.TemporaryDirectory() as d:
            sm = SessionManager(sessions_dir=d)
            info = sm.create_session("test_ltm")
            ltm = sm.get_long_term_memory(info["id"])
            assert ltm is not None
            ltm2 = sm.get_long_term_memory(info["id"])
            assert ltm2 is ltm


class TestSessionManagerEdgeCases:
    def test_list_sessions_does_not_mutate_index(self):
        with tempfile.TemporaryDirectory() as d:
            sm = SessionManager(sessions_dir=d)
            info = sm.create_session("s1")
            sid = info["id"]
            index_path = os.path.join(d, "index.json")
            with open(index_path, "r") as f:
                raw_before = json.load(f)
            s1_raw_before = raw_before["sessions"][sid]

            sm.list_sessions()

            with open(index_path, "r") as f:
                raw_after = json.load(f)
            s1_raw_after = raw_after["sessions"][sid]

            assert s1_raw_before["turn_count"] == s1_raw_after["turn_count"]

    def test_get_session_nonexistent(self):
        with tempfile.TemporaryDirectory() as d:
            sm = SessionManager(sessions_dir=d)
            with pytest.raises(ValueError):
                sm.get_session("nonexistent_session_id_xyz")

    def test_delete_nonexistent_session(self):
        with tempfile.TemporaryDirectory() as d:
            sm = SessionManager(sessions_dir=d)
            sm.delete_session("nonexistent_session_id_xyz")

    def test_rename_session(self):
        with tempfile.TemporaryDirectory() as d:
            sm = SessionManager(sessions_dir=d)
            info = sm.create_session("old_name")
            sm.rename_session(info["id"], "new_name")
            assert sm._index["sessions"][info["id"]]["name"] == "new_name"
