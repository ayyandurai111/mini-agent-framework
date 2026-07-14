"""
core/tool_loop.py
--------------------
ReAct-style tool execution loop. The LLM responds with JSON each turn:
either a tool_call (to run a function) or a final answer (to exit).

Supports configurable exit_keys so the same loop works for both worker
agents (exit on "final_answer") and the orchestrator planner (exit on
"needs_sub_agents").
"""

import sys
from typing import Callable, List, Optional, Union

from ..llm.base import BaseLLMProvider
from .utils.action_tracker import ActionTracker
from .utils.json_utils import try_parse_json
from ..registry.tools import Tool


def run_with_tools(
    llm_provider: BaseLLMProvider,
    system_prompt: str,
    task: str,
    tools: List[Tool],
    max_iterations: int = 5,
    approval_callback: Optional[Callable[[str, dict], bool]] = None,
    action_tracker: ActionTracker = None,
    agent_id: str = "",
    exit_keys: Union[str, List[str]] = "final_answer",
    return_parsed: bool = False,
) -> str:
    tool_map = {tool.name: tool for tool in tools}
    transcript = task
    last_raw_response = ""
    iteration = 0

    if isinstance(exit_keys, str):
        exit_keys = [exit_keys]

    while True:
        if iteration >= max_iterations:
            print(f"\n  (Reached {max_iterations} tool calls. Continue? y/n: ", end="", file=sys.stderr)
            try:
                choice = input().strip().lower()
            except (EOFError, KeyboardInterrupt):
                choice = "n"
            if choice == "y":
                iteration = 0
                continue
            return (
                f"(Stopped after {max_iterations} tool calls without a final answer.) "
                f"Last response: {last_raw_response}"
            )

        try:
            last_raw_response = llm_provider.generate(system_prompt=system_prompt, user_message=transcript)
        except Exception as exc:
            return f"(LLM call failed during agent execution: {exc})"
        parsed = try_parse_json(last_raw_response)

        if parsed is None:
            return last_raw_response

        for key in exit_keys:
            if key in parsed:
                if return_parsed:
                    return parsed
                value = parsed[key]
                return str(value) if not isinstance(value, str) else value

        if tool_call := parsed.get("tool_call"):
            if tool_call == "final_answer":
                args = parsed.get("arguments", {}) or {}
                answer = args.get("answer", "") or ""
                if answer:
                    return str(answer)
                if "response" in args:
                    return str(args["response"])
                return last_raw_response
            if tool_call == "result":
                tool_call = "final_answer"
                parsed["tool_call"] = "final_answer"
            tool_name = tool_call
            arguments = parsed.get("arguments") or {}
            tool = tool_map.get(tool_name)

            if action_tracker:
                action_tracker.on_tool_call(agent_id, tool_name, arguments, iteration=iteration + 1, total=max_iterations)

            if tool is None:
                tool_result = f"Error: tool '{tool_name}' is not available to you."
            elif tool.requires_approval and approval_callback is not None and not approval_callback(tool_name, arguments):
                tool_result = (
                    "The user did not approve this action. Do not repeat it \u2014 "
                    "choose a different approach, or explain why it was needed "
                    "in your final answer."
                )
            else:
                try:
                    tool_result = tool.run(**arguments)
                except Exception as exc:
                    tool_result = f"Error running tool '{tool_name}': {exc}"

            if action_tracker:
                action_tracker.on_tool_result(agent_id, tool_name, tool_result)

            transcript += (
                f"\n\nYou called {tool_name} with arguments {arguments}.\n"
                f"Result: {tool_result}\n\n"
                f"Continue the task. Respond with another tool_call JSON, "
                f"or a {'/'.join(exit_keys)} JSON if you now have everything you need."
            )
            iteration += 1
            continue

        return last_raw_response
