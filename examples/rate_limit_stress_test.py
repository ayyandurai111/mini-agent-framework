"""
Rate-limit stress test for NVIDIA NIM free tier (~40 RPM).

Tests:
  1. Burst: 10 rapid sequential calls → measures how many succeed before 429
  2. Backoff: verifies retry with exponential backoff recovers after wait
  3. Concurrent: 5 parallel calls → simulates multi-agent burst
  4. Sustained: 60s window → counts how many calls complete in 1 minute
"""

import os
import sys
import json
import time
import threading
from datetime import datetime, timedelta

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from mini_agent.providers.nvidia_provider import NvidiaProvider, RECOMMENDED_MODELS


API_KEY = os.environ.get("NVIDIA_API_KEY")
if not API_KEY:
    raise SystemExit("Set NVIDIA_API_KEY environment variable first")

MODEL = "deepseek-ai/deepseek-v4-flash"
RESULTS = {}


def test_burst(provider, n=10):
    print(f"\n{'='*60}")
    print(f"TEST 1: Burst — {n} rapid sequential calls")
    print(f"{'='*60}")
    successes, failures = 0, 0
    for i in range(n):
        try:
            start = time.time()
            resp = provider.generate("Say 'hello' and nothing else.", f"Call #{i+1}")
            elapsed = time.time() - start
            print(f"  [{i+1}/{n}] OK ({elapsed:.1f}s): {resp.strip()[:60]}")
            successes += 1
        except Exception as e:
            elapsed = time.time() - start
            err = str(e)[:80]
            print(f"  [{i+1}/{n}] FAIL ({elapsed:.1f}s): {err}")
            failures += 1
    RESULTS["burst"] = {"success": successes, "failure": failures}
    print(f"  Result: {successes} succeeded, {failures} failed")
    return successes, failures


def test_backoff(provider):
    print(f"\n{'='*60}")
    print(f"TEST 2: Backoff — verify retry recovers after 429")
    print(f"{'='*60}")
    # Hit the rate limit hard first
    for _ in range(5):
        try:
            provider.generate("Say 'x'", "x")
        except Exception:
            pass

    # Now try with backoff — use a provider with more retries
    patient_provider = NvidiaProvider(api_key=API_KEY, model=MODEL, max_retries=6)
    start = time.time()
    for attempt in range(3):
        try:
            resp = patient_provider.generate("Say 'recovered' and nothing else.", f"attempt {attempt}")
            elapsed = time.time() - start
            print(f"  OK after {elapsed:.1f}s: {resp.strip()[:60]}")
            RESULTS["backoff"] = {"recovered": True, "time": round(elapsed, 1)}
            return True
        except Exception as e:
            elapsed = time.time() - start
            print(f"  Failed at {elapsed:.1f}s: {str(e)[:60]}")
    RESULTS["backoff"] = {"recovered": False}
    return False


def test_concurrent(provider, n=5):
    print(f"\n{'='*60}")
    print(f"TEST 3: Concurrent — {n} parallel calls")
    print(f"{'='*60}")

    lock = threading.Lock()
    results = {"ok": 0, "fail": 0, "errors": []}

    def worker(i):
        try:
            start = time.time()
            resp = provider.generate("Say 'concurrent' and nothing else.", f"thread {i}")
            elapsed = time.time() - start
            with lock:
                results["ok"] += 1
                print(f"  [T{i}] OK ({elapsed:.1f}s)")
        except Exception as e:
            with lock:
                results["fail"] += 1
                results["errors"].append(str(e)[:60])
                print(f"  [T{i}] FAIL: {str(e)[:60]}")

    threads = [threading.Thread(target=worker, args=(i,)) for i in range(n)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    RESULTS["concurrent"] = results
    print(f"  Result: {results['ok']} ok, {results['fail']} failed")
    return results


def test_sustained(provider, duration=60):
    print(f"\n{'='*60}")
    print(f"TEST 4: Sustained — {duration}s window, count successful calls")
    print(f"{'='*60}")

    count = 0
    start = time.time()
    deadline = start + duration
    while time.time() < deadline:
        try:
            provider.generate("Say 'tick'", f"tick {count}")
            count += 1
            remaining = int(deadline - time.time())
            print(f"  OK ({count} total, {remaining}s left)")
        except Exception:
            time.sleep(2)
    total_time = time.time() - start
    rpm = count / (total_time / 60)
    RESULTS["sustained"] = {"calls": count, "rpm": round(rpm, 1)}
    print(f"  Result: {count} calls in {total_time:.0f}s → {rpm:.1f} RPM")
    return count, rpm


def test_model_list(provider):
    print(f"\n{'='*60}")
    print(f"TEST 5: Model availability — test all RECOMMENDED_MODELS")
    print(f"{'='*60}")
    results = {}
    for model in RECOMMENDED_MODELS:
        p = NvidiaProvider(api_key=API_KEY, model=model, max_retries=1)
        try:
            start = time.time()
            resp = p.generate("Say 'ok'", f"test {model}")
            elapsed = time.time() - start
            results[model] = {"status": "ok", "time": round(elapsed, 1)}
            print(f"  OK ({elapsed:.1f}s): {model}")
        except Exception as e:
            results[model] = {"status": "fail", "error": str(e)[:60]}
            print(f"  FAIL: {model} — {str(e)[:60]}")
    RESULTS["models"] = results
    return results


if __name__ == "__main__":
    print(f"NVIDIA API Key: {API_KEY[:12]}...{API_KEY[-4:]}")
    print(f"Model: {MODEL}")
    print(f"Recommended models available: {len(RECOMMENDED_MODELS)}")

    provider = NvidiaProvider(api_key=API_KEY, model=MODEL, max_retries=2)

    test_burst(provider, n=10)
    time.sleep(5)
    test_backoff(provider)
    time.sleep(5)
    test_concurrent(provider, n=5)
    time.sleep(5)
    test_sustained(provider, duration=60)
    time.sleep(5)
    test_model_list(provider)

    print(f"\n{'='*60}")
    print("SUMMARY")
    print(f"{'='*60}")
    print(json.dumps(RESULTS, indent=2))

    rpm = RESULTS.get("sustained", {}).get("rpm", 0)
    burst_ok = RESULTS.get("burst", {}).get("success", 0)
    concurrent_ok = RESULTS.get("concurrent", {}).get("ok", 0)

    print(f"\nVerdict: ~{rpm} RPM sustained | Burst: {burst_ok}/10 ok | Concurrent: {concurrent_ok}/5 ok")
    print(f"Backoff: {'RECOVERED' if RESULTS.get('backoff', {}).get('recovered') else 'FAILED'}")
