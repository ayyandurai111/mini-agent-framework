"""
core/orchestrator.py
-----------------------
Plans tasks, spawns agents with matched tools/skills, and aggregates results.
"""

from concurrent.futures import ThreadPoolExecutor, as_completed

from typing import List

from ..llm.base import BaseLLMProvider
from .utils.action_tracker import ActionTracker, console_event_logger
from .agent import Agent
from .tool_loop import run_with_tools
from .utils.json_utils import try_parse_json
from .memory.conversation import ConversationMemory
from ..registry.tools import ToolRegistry
from ..prompts.orchestrator_prompt import ORCHESTRATOR_SYSTEM_PROMPT
from ..config.settings import MAX_AGENTS, MAX_RECURSION_DEPTH
from ..skills import Skill, SkillRegistry, read_skill_content, discover_package_skills


class Orchestrator:
    def __init__(self, llm_provider: BaseLLMProvider, max_agents: int = MAX_AGENTS,
                 approval_callback=None, memory_file: str = None,
                 action_tracker: ActionTracker = None):
        if llm_provider is None:
            raise ValueError(
                "llm_provider is required. Implement BaseLLMProvider and pass an instance."
            )
        self.llm_provider = llm_provider
        self.max_agents = max_agents
        self.tool_registry = ToolRegistry()
        self.active_agents = {}
        # approval_callback: (tool_name, arguments) -> bool. If set, any Tool
        # with requires_approval=True will ask before running (see core/approval.py).
        self.approval_callback = approval_callback
        # Live action event tracker â€” emits plan, agent, tool events
        self.action_tracker = action_tracker or ActionTracker(on_event=console_event_logger)
        self.skill_registry = SkillRegistry()
        for skill in discover_package_skills():
            self.skill_registry.register(skill)
        # Session-level LLM-compressed memory â€” saves tokens by summarizing
        # past agent runs instead of passing raw transcripts.
        self.conversation_memory = (
            ConversationMemory(llm_provider=llm_provider, persist_file=memory_file)
            if memory_file
            else ConversationMemory(llm_provider=llm_provider)
        )

    def register_tool(self, tool):
        """Register a single custom tool."""
        self.tool_registry.register(tool)

    def register_tools(self, tools: list):
        """Register multiple tools at once (e.g. BUILTIN_TOOLS)."""
        for tool in tools:
            self.tool_registry.register(tool)

    def register_skill(self, skill: Skill):
        self.skill_registry.register(skill)

    def register_skills(self, skills: list):
        for skill in skills:
            self.skill_registry.register(skill)

    def load_skills_from_dir(self, directory: str):
        """Load all .md skill files from a directory."""
        for skill in self.skill_registry.load_from_dir(directory):
            self.skill_registry.register(skill)

    def _build_skills_context(self, skills: List[Skill]) -> str:
        if not skills:
            return ""
        blocks = []
        for skill in skills:
            content = read_skill_content(skill)
            blocks.append(f"[SKILL: {skill.name}]\n{content}")
        return "\n\n".join(blocks)

    def _match_skills(self, task: str, instructions: str = "") -> List[Skill]:
        combined = f"{task} {instructions}"
        return self.skill_registry.match(combined)

    def _plan(self, task: str) -> dict:
        system_prompt = ORCHESTRATOR_SYSTEM_PROMPT

        tool_names = self.tool_registry.list_available()
        tool_descs = []
        for name in tool_names:
            t = self.tool_registry.get(name)
            if t:
                tool_descs.append(f"  - {t.describe()}")
        if tool_descs:
            system_prompt += f"\nAVAILABLE TOOLS:\n" + "\n".join(tool_descs) + "\n"

        skill_names = self.skill_registry.list()
        skill_descs = [f"  - {self.skill_registry.get(s).describe()}" for s in skill_names]
        if skill_descs:
            system_prompt += f"\nSKILLS AVAILABLE:\n" + "\n".join(skill_descs) + "\n"

        read_only_names = self.tool_registry.get_read_only()
        read_only_tools = [
            self.tool_registry.get(n) for n in read_only_names
            if self.tool_registry.get(n) is not None
        ]

        try:
            raw_response = run_with_tools(
                llm_provider=self.llm_provider,
                system_prompt=system_prompt,
                task=task,
                tools=read_only_tools,
                max_iterations=2,
                exit_keys=["needs_sub_agents"],
                return_parsed=True,
                action_tracker=self.action_tracker,
                agent_id="planner",
            )
        except Exception:
            plan = {"needs_sub_agents": False, "direct_answer": "", "sub_tasks": []}
            self.action_tracker.on_plan(task, plan["needs_sub_agents"], plan["sub_tasks"], tools_count=0, skills_available=[], required_capabilities=[])
            return plan

        if isinstance(raw_response, dict):
            plan = raw_response
        else:
            parsed = try_parse_json(raw_response)
            plan = parsed if isinstance(parsed, dict) else {"needs_sub_agents": False, "direct_answer": "", "sub_tasks": []}

        self.action_tracker.on_plan(
            task,
            plan.get("needs_sub_agents", False),
            plan.get("sub_tasks", []),
            tools_count=len(tool_names),
            skills_available=list(self.skill_registry.list()),
            required_capabilities=plan.get("required_capabilities", []),
        )
        return plan

    def spawn_agent(self, role: str, instructions: str, capability_names: list, depth: int = 0,
                    skills_context: str = "", skill_names: list = None) -> Agent:
        if len(self.active_agents) >= self.max_agents:
            raise RuntimeError(f"MAX_AGENTS limit ({self.max_agents}) reached.")
        if depth > MAX_RECURSION_DEPTH:
            raise RuntimeError(f"MAX_RECURSION_DEPTH ({MAX_RECURSION_DEPTH}) exceeded.")

        tools = self.tool_registry.match(capability_names, role=role)
        agent = Agent(
            role=role,
            instructions=instructions,
            llm_provider=self.llm_provider,
            tools=tools,
            depth=depth,
            spawn_callback=self.spawn_agent,   # enables recursive spawning
            approval_callback=self.approval_callback,
            conversation_summary=self.conversation_memory.get_context(),
            action_tracker=self.action_tracker,
            skills_context=skills_context,
        )
        self.active_agents[agent.id] = agent
        self.action_tracker.on_agent_start(agent.id, role, instructions, capabilities=capability_names, skills=skill_names or [])
        return agent

    def _run_agents_need_based(self, sub_tasks: list) -> dict:
        n = len(sub_tasks)
        deps = [set(t.get("depends_on", [])) for t in sub_tasks]

        executed = set()
        levels = []
        while len(executed) < n:
            level = [i for i in range(n) if i not in executed and deps[i].issubset(executed)]
            if not level:
                raise RuntimeError(f"Circular dependency in sub-tasks: {sub_tasks}")
            levels.append(level)
            executed.update(level)

        agent_map = {}
        results = {}
        for level in levels:
            with ThreadPoolExecutor(max_workers=min(len(level), self.max_agents)) as executor:
                future_to_idx = {}
                for idx in level:
                    task = sub_tasks[idx]
                    cap_names = task.get("required_capabilities", [])
                    skill_name = task.get("skill", "")
                    skills_context = ""
                    if skill_name:
                        skill = self.skill_registry.get(skill_name)
                        if skill:
                            skills_context = f"[SKILL: {skill.name}]\n{read_skill_content(skill)}"
                    agent = self.spawn_agent(
                        role=task.get("role", "worker"),
                        instructions=task.get("instructions", ""),
                        capability_names=cap_names,
                        skills_context=skills_context,
                        skill_names=[skill_name] if skill_name else [],
                    )
                    agent_map[idx] = agent.id
                    future_to_idx[executor.submit(agent.run)] = idx

                for future in as_completed(future_to_idx):
                    idx = future_to_idx[future]
                    try:
                        result = future.result()
                        results[agent_map[idx]] = result
                        agent_id = agent_map[idx]
                        self.action_tracker.on_agent_end(agent_id, sub_tasks[idx].get("role", "worker"), result)
                        self.conversation_memory.add_entry(
                            role=sub_tasks[idx].get("role", "worker"),
                            content=f"[{agent_id}] {result}",
                        )
                    except Exception as exc:
                        results[agent_map[idx]] = f"Agent error: {exc}"
                        self.action_tracker.on_agent_end(agent_map[idx], sub_tasks[idx].get("role", "worker"), f"Agent error: {exc}")
        return results

    def run(self, task: str) -> dict:
        self.active_agents.clear()

        plan = self._plan(task)

        matched_skills = self._match_skills(task)
        skills_context = self._build_skills_context(matched_skills)

        if not plan.get("needs_sub_agents"):
            capability_names = plan.get("required_capabilities") or self.tool_registry.get_read_only()
            agent = self.spawn_agent(
                role="direct_agent",
                instructions=f"Task: {task}",
                capability_names=capability_names,
                skills_context=skills_context,
                skill_names=[s.name for s in matched_skills],
            )
            try:
                result = agent.run()
            except Exception as exc:
                result = f"Agent execution failed: {exc}"
            self.action_tracker.on_agent_end(agent.id, "direct_agent", result)
            self.conversation_memory.add_entry(role="direct_agent", content=result)
            return {"final_answer": result, "sub_agent_results": {agent.id: result}}

        sub_tasks = plan.get("sub_tasks", [])[: self.max_agents]
        results = self._run_agents_need_based(sub_tasks)

        self.action_tracker.on_aggregate(task)
        final_answer = self._aggregate(task, results)
        return {"final_answer": final_answer, "sub_agent_results": results}

    def _aggregate(self, original_task: str, results: dict) -> str:
        if not results:
            return "No results to aggregate."
        combined = "\n\n".join(f"[{agent_id}]\n{output}" for agent_id, output in results.items())
        try:
            aggregation_prompt = (
                f"Original task: {original_task}\n\n"
                f"Sub-agent results below:\n\n{combined}\n\n"
                f"Synthesize these into one clear, complete final answer. "
                f"Output only the final answer â€” no meta-commentary."
            )
            return self.llm_provider.generate(
                system_prompt="You are an Aggregator AI that merges sub-agent outputs into one coherent final answer.",
                user_message=aggregation_prompt,
            )
        except (OSError, RuntimeError, ValueError):
            return f"[Aggregation fallback â€” raw sub-agent results]\n\n{combined}"
