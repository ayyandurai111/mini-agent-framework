"""mini_agent — interactive chatbot demo."""

import os

from mini_agent import Orchestrator, Tool, BaseLLMProvider, ActionTracker
from mini_agent.core import auto_approve_callback
from mini_agent.registry.builtin import (
    FILE_TOOLS, WEB_TOOLS, MATH_TOOLS, DATA_TOOLS, SYSTEM_TOOLS, BASH_TOOL,
    BROWSER_TOOLS,
)


# ── LLM Provider ──────────────────────────────────────────────
def get_llm():
    api_key = os.environ.get("NVIDIA_API_KEY")
    if api_key and api_key.startswith("nvapi-"):
        from concurrent.futures import ThreadPoolExecutor, TimeoutError
        with ThreadPoolExecutor(max_workers=1) as ex:
            fut = ex.submit(_try_nvidia, api_key)
            try:
                return fut.result(timeout=150)
            except TimeoutError:
                print("  [NVIDIA connection timed out - using mock]")
            except Exception as e:
                print(f"  [NVIDIA init failed: {e}]")

    print("  [Using mock LLM - set NVIDIA_API_KEY for real AI]")
    print("  $env:NVIDIA_API_KEY = \"nvapi-...\"\n")

    class MockProvider(BaseLLMProvider):
        def generate(self, system_prompt: str, user_message: str) -> str:
            task = user_message[-200:]
            if "date" in task.lower():
                from datetime import datetime
                return '{"final_answer": "Today is ' + datetime.now().strftime('%Y-%m-%d') + '."}'
            if "hello" in task.lower() or "hi" in task.lower():
                return '{"final_answer": "Hello! How can I help you?"}'
            return '{"final_answer": "Mock answer - set NVIDIA_API_KEY for real AI."}'
    return MockProvider()


def _try_nvidia(api_key):
    from mini_agent.providers.nvidia_provider import NvidiaProvider
    return NvidiaProvider(api_key=api_key)


# ── Custom tools ──────────────────────────────────────────────
def make_calculator():
    import math
    def calculate(expression: str) -> str:
        allowed = {"abs": abs, "round": round, "min": min, "max": max,
                   "sum": sum, "len": len, "math": math}
        try:
            r = eval(expression, {"__builtins__": {}}, allowed)
            return f"{expression} = {r}"
        except Exception as e:
            return f"Error: {e}"
    return Tool(name="calculator", description="Evaluate a math expression",
                func=calculate, read_only=True)


def make_date_tool():
    from datetime import datetime
    def get_date(format: str = "%Y-%m-%d") -> str:
        return datetime.now().strftime(format)
    return Tool(name="get_date", description="Get the current date",
                func=get_date, read_only=True)


# ── Chatbot ───────────────────────────────────────────────────
def main():
    provider = get_llm()
    print("=" * 60)
    print("  mini_agent - Interactive Chatbot")
    print("=" * 60)

    # Use a simple ASCII-only tracker instead of the default unicode box-drawing
    def ascii_tracker(event_type, data):
        if event_type == "plan":
            needs = "single" if not data["needs_sub_agents"] else f"multi ({len(data.get('sub_tasks',[]))} agents)"
            print(f"  [PLAN] {needs}")
        elif event_type == "agent_start":
            print(f"  [AGENT] {data.get('role', '?')}")
        elif event_type == "tool_call":
            print(f"    calling {data.get('tool', '?')}()")
        elif event_type == "agent_end":
            r = str(data.get("result", ""))[:80]
            print(f"    -> {r}")

    tracker = ActionTracker(on_event=ascii_tracker)

    orchestrator = Orchestrator(
        llm_provider=provider,
        action_tracker=tracker,
        approval_callback=auto_approve_callback,
    )
    orchestrator.register_tool(make_calculator())
    orchestrator.register_tool(make_date_tool())
    orchestrator.register_tools(FILE_TOOLS)
    orchestrator.register_tools(WEB_TOOLS)
    orchestrator.register_tools(MATH_TOOLS)
    orchestrator.register_tools(DATA_TOOLS)
    orchestrator.register_tools(SYSTEM_TOOLS)
    orchestrator.register_tools(BASH_TOOL)
    orchestrator.register_tools(BROWSER_TOOLS)

    tool_names = orchestrator.tool_registry.list_available()
    skill_names = orchestrator.skill_registry.list()
    print(f"  Tools ({len(tool_names)}): {', '.join(sorted(tool_names))}")
    print(f"  Skills ({len(skill_names)}): {', '.join(skill_names)}")
    print(f"  Memory: last 2 turns injected into main agent only (sub-agents start fresh)\n")
    print("  Type 'exit' to quit, 'memory' to see history\n")

    while True:
        try:
            user_input = input("You > ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break

        if not user_input:
            continue
        if user_input.lower() in ("exit", "quit"):
            break
        if user_input.lower() == "memory":
            turns = orchestrator.conversation_memory.raw_turns()
            if not turns:
                print("  (no history)")
            else:
                for i, t in enumerate(turns, 1):
                    print(f"\n--- Turn {i} ---")
                    print(t[:400])
                    if len(t) > 400:
                        print("  ...")
            continue

        print(f"\n  -- Processing --")
        result = orchestrator.run(user_input)
        answer = result.get("final_answer", "(no answer)")
        print(f"\n  Answer: {answer}\n")


if __name__ == "__main__":
    main()
