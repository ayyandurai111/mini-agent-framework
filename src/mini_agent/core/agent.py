"""
core/agent.py
---------------
Worker that executes one task via the tool-execution loop.
"""

import uuid

from ..llm.base import BaseLLMProvider
from ..config.settings import MAX_TOOL_ITERATIONS
from .utils.action_tracker import ActionTracker
from .tool_loop import run_with_tools
from ..prompts.prompt_builder import build_agent_system_prompt


class Agent:
    def __init__(
        self,
        role: str,
        instructions: str,
        llm_provider: BaseLLMProvider,
        tools: list = None,
        depth: int = 0,
        spawn_callback=None,        # reference to orchestrator.spawn_agent, for recursion
        approval_callback=None,     # (tool_name, arguments) -> bool, for gated tools
        session_memory: str = "",
        action_tracker: ActionTracker = None,  # live action events
        skills_context: str = "",   # matched skill instructions injected into prompt
    ):
        self.id = f"{role.replace(' ', '_')}_{uuid.uuid4().hex[:6]}"
        self.role = role
        self.instructions = instructions
        self.llm_provider = llm_provider
        self.tools = tools or []
        self.depth = depth
        self.spawn_callback = spawn_callback
        self.approval_callback = approval_callback
        self.session_memory = session_memory
        self.action_tracker = action_tracker
        self.skills_context = skills_context
        self.status = "idle"

    def run(self) -> dict:
        """Executes the agent's task. Returns dict with response and tool_calls."""
        self.status = "running"

        system_prompt = build_agent_system_prompt(
            self.role, self.instructions, self.tools,
            session_memory=self.session_memory,
            skills_context=self.skills_context,
        )

        tool_history = []
        final_text = run_with_tools(
            llm_provider=self.llm_provider,
            system_prompt=system_prompt,
            task=self.instructions,
            tools=self.tools,
            max_iterations=MAX_TOOL_ITERATIONS,
            approval_callback=self.approval_callback,
            action_tracker=self.action_tracker,
            agent_id=self.id,
            tool_history=tool_history,
        )

        self.status = "done"
        return {
            "response": final_text,
            "tool_calls": tool_history,
        }
