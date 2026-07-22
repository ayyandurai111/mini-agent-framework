"""
Real integration test — benchmarks all confirmed-working NVIDIA NIM models.
Skipped if NVIDIA_API_KEY is not set.
"""
import os, time
import pytest

pytestmark = pytest.mark.skipif(
    not os.environ.get("NVIDIA_API_KEY", "").startswith("nvapi-"),
    reason="NVIDIA_API_KEY not set or invalid"
)

# All models confirmed working via real API benchmark.
# Sorted by speed (fastest first).
CONFIRMED_WORKING = [
    ("nvidia/nemotron-mini-4b-instruct",       "4B"),
    ("meta/llama-3.1-8b-instruct",             "8B"),
    ("meta/llama-3.1-70b-instruct",            "70B"),
    ("nvidia/llama-3.3-nemotron-super-49b-v1", "49B"),
    ("deepseek-ai/deepseek-v4-flash",          "284B"),
    ("nvidia/nemotron-3-ultra-550b-a55b",      "550B"),
    ("google/gemma-4-31b-it",                  "31B"),
    ("poolside/laguna-xs-2.1",                 "33B"),
    ("mistralai/mistral-small-4-119b-2603",    "119B"),
    ("mistralai/mistral-medium-3.5-128b",      "128B"),
    ("deepseek-ai/deepseek-v4-pro",            "1.6T"),
    ("mistralai/mistral-large-3-675b-instruct-2512", "675B"),
    ("z-ai/glm-5.2",                           "?"),
]

PROMPT = "What is Python? Answer in one short sentence."


class TestFullPipeline:
    """Full Orchestrator pipeline with default model."""

    def test_direct_answer(self):
        from mini_agent import Orchestrator, NvidiaProvider
        llm = NvidiaProvider(model="deepseek-ai/deepseek-v4-flash", temperature=0.1, max_tokens=256)
        orch = Orchestrator(llm)
        result = orch.run("What is 2+2? Answer in one word.")
        assert "4" in result["final_answer"] or "four" in result["final_answer"].lower()

    def test_chat_streaming(self):
        from mini_agent import Orchestrator, NvidiaProvider
        llm = NvidiaProvider(model="deepseek-ai/deepseek-v4-flash", temperature=0.1, max_tokens=256)
        orch = Orchestrator(llm)
        result = orch.chat("Say hello in one word.")
        assert len(result) > 0


@pytest.mark.parametrize("model_id,_", CONFIRMED_WORKING)
class TestAllModels:
    """Every confirmed-working model responds correctly."""

    def test_responds(self, model_id, _):
        from mini_agent import NvidiaProvider
        llm = NvidiaProvider(model=model_id, temperature=0.1, max_tokens=100, max_retries=1)
        start = time.time()
        response = llm.generate("You are helpful.", PROMPT)
        elapsed = time.time() - start
        assert len(response.strip()) > 0
        print(f"\n    {model_id}: {elapsed:.1f}s => {response.strip()[:80]}")
