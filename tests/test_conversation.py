"""Tests for ConversationMemory."""
import json
import os
import tempfile

import pytest
from mini_agent.core.memory.conversation import ConversationMemory


class TestConversationMemory:
    def test_new_memory_empty(self):
        mem = ConversationMemory(max_turns=10, persist_file="")
        assert len(mem._turns) == 0

    def test_add_turn(self):
        mem = ConversationMemory(max_turns=10, persist_file="")
        mem.add_turn("user message", {"needs_sub_agents": False}, [], "assistant response")
        assert len(mem._turns) == 1

    def test_max_turns_respected(self):
        mem = ConversationMemory(max_turns=3, persist_file="")
        for i in range(5):
            mem.add_turn(f"msg {i}", {"needs_sub_agents": False}, [], f"resp {i}")
        assert len(mem._turns) == 3

    def test_max_turns_zero_unlimited(self):
        mem = ConversationMemory(max_turns=0, persist_file="")
        for i in range(100):
            mem.add_turn(f"msg {i}", {"needs_sub_agents": False}, [], f"resp {i}")
        assert len(mem._turns) == 100

    def test_get_context(self):
        mem = ConversationMemory(max_turns=10, persist_file="")
        mem.add_turn("hello", {"needs_sub_agents": False}, [], "hi there")
        ctx = mem.get_context()
        assert "hello" in ctx
        assert "hi there" in ctx

    def test_persist_and_load(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            path = f.name
        try:
            mem = ConversationMemory(max_turns=10, persist_file=path)
            mem.add_turn("test", {"needs_sub_agents": False}, [], "response")

            mem2 = ConversationMemory(max_turns=10, persist_file=path)
            assert len(mem2._turns) == 1
            assert "test" in mem2._turns[0]
        finally:
            os.unlink(path)

    def test_clear_memory(self):
        mem = ConversationMemory(max_turns=10, persist_file="")
        mem.add_turn("test", {"needs_sub_agents": False}, [], "response")
        mem.clear()
        assert len(mem._turns) == 0
        assert mem._turn_counter == 0

    def test_inject_long_term(self):
        mem = ConversationMemory(max_turns=10, persist_file="")
        mem.inject_long_term(rules_text="Be concise", summary_text="Previous talk about Python")
        ctx = mem.get_context()
        assert "Be concise" in ctx
        assert "Python" in ctx

    def test_search(self):
        mem = ConversationMemory(max_turns=10, persist_file="")
        mem.add_turn("What is Python?", {"needs_sub_agents": False}, [], "A programming language")
        results = mem.search("Python")
        assert len(results) == 1
        assert results[0]["turn_index"] == 0

    def test_search_no_match(self):
        mem = ConversationMemory(max_turns=10, persist_file="")
        mem.add_turn("Hello", {"needs_sub_agents": False}, [], "Hi")
        results = mem.search("Ruby")
        assert len(results) == 0

    def test_token_count(self):
        mem = ConversationMemory(max_turns=10, persist_file="")
        mem.add_turn("test", {"needs_sub_agents": False}, [], "response")
        counts = mem.count_tokens_in_turns()
        assert len(counts) == 1
        assert counts[0] > 0

    def test_raw_turns_returns_copy(self):
        mem = ConversationMemory(max_turns=10, persist_file="")
        mem.add_turn("test", {"needs_sub_agents": False}, [], "response")
        turns = mem.raw_turns()
        turns.append("extra")
        assert len(mem._turns) == 1

    def test_context_respects_budget(self):
        mem = ConversationMemory(max_turns=100, persist_file="")
        long_text = "word " * 5000
        mem.add_turn(long_text, {"needs_sub_agents": False}, [], long_text)
        ctx = mem.get_context()
        assert len(ctx) < 100000
