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
from ..skills import Skill, SkillRegistry, read_skill_content


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
        # Session memory - stores raw-text conversation turns for context
        self.conversation_memory = (
            ConversationMemory(persist_file=memory_file)
            if memory_file
            else ConversationMemory()
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

    def _plan(self, task: str, session_memory: str = "") -> dict:
        system_prompt = ORCHESTRATOR_SYSTEM_PROMPT
        if session_memory:
            system_prompt += f"\n\n## CONVERSATION HISTORY\n{session_memory}\n"

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
                exit_keys=["final_answer", "needs_sub_agents"],
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
                    skills_context: str = "", skill_names: list = None,
                    session_memory: str = "") -> Agent:
        if len(self.active_agents) >= self.max_agents:
            raise RuntimeError(f"MAX_AGENTS limit ({self.max_agents}) reached.")
        if depth > MAX_RECURSION_DEPTH:
            raise RuntimeError(f"MAX_RECURSION_DEPTH ({MAX_RECURSION_DEPTH}) exceeded.")

        tools = self.tool_registry.match(capability_names)
        agent = Agent(
            role=role,
            instructions=instructions,
            llm_provider=self.llm_provider,
            tools=tools,
            depth=depth,
            spawn_callback=self.spawn_agent,
            approval_callback=self.approval_callback,
            session_memory=session_memory,
            action_tracker=self.action_tracker,
            skills_context=skills_context,
        )
        self.active_agents[agent.id] = agent
        self.action_tracker.on_agent_start(agent.id, role, instructions, capabilities=capability_names, skills=skill_names or [])
        return agent

    def _run_agents_need_based(self, sub_tasks: list):
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
        agents_data = []
        dep_results = {}
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

                    session_memory = ""
                    if task.get("memory", False):
                        dep_parts = []
                        for dep_idx in task.get("depends_on", []):
                            if dep_idx in dep_results:
                                dep_role = sub_tasks[dep_idx].get("role", "?")
                                dep_resp = dep_results[dep_idx].get("response", str(dep_results[dep_idx]))[:500]
                                dep_parts.append(
                                    f"Agent[{dep_idx}] ({dep_role}):\n{dep_resp}"
                                )
                        if dep_parts:
                            session_memory = (
                                "=== DEPENDENCY RESULTS ===\n"
                                "Below are results from agents this task depends on. "
                                "Use them to complete your work:\n\n"
                                + "\n\n".join(dep_parts)
                            )

                    agent = self.spawn_agent(
                        role=task.get("role", "worker"),
                        instructions=task.get("instructions", ""),
                        capability_names=cap_names,
                        skills_context=skills_context,
                        skill_names=[skill_name] if skill_name else [],
                        session_memory=session_memory,
                    )
                    agent_map[idx] = agent.id
                    future_to_idx[executor.submit(agent.run)] = idx

                for future in as_completed(future_to_idx):
                    idx = future_to_idx[future]
                    try:
                        result = future.result()
                        results[agent_map[idx]] = result
                        dep_results[idx] = result
                        agent_id = agent_map[idx]
                        role = sub_tasks[idx].get("role", "worker")
                        response_text = result.get("response", str(result))
                        self.action_tracker.on_agent_end(agent_id, role, response_text)
                        agents_data.append({
                            "index": idx,
                            "role": role,
                            "response": response_text,
                            "tool_calls": result.get("tool_calls", []),
                        })
                    except Exception as exc:
                        results[agent_map[idx]] = {"response": f"Agent error: {exc}", "tool_calls": []}
                        dep_results[idx] = results[agent_map[idx]]
                        self.action_tracker.on_agent_end(agent_map[idx], sub_tasks[idx].get("role", "worker"), f"Agent error: {exc}")
        return agents_data, results

    def run(self, task: str) -> dict:
        self.active_agents.clear()

        plan = self._plan(task, session_memory=self.conversation_memory.get_context())

        if "final_answer" in plan:
            answer = plan["final_answer"]
            self.conversation_memory.add_turn(task, plan, [], answer)
            return {"final_answer": answer, "sub_agent_results": {}}

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
                session_memory=self.conversation_memory.get_context(),
            )
            try:
                result = agent.run()
            except Exception as exc:
                result = {"response": f"Agent execution failed: {exc}", "tool_calls": []}
            response_text = result.get("response", str(result))
            self.action_tracker.on_agent_end(agent.id, "direct_agent", response_text)
            agents_data = [{
                "index": None,
                "role": "direct_agent",
                "response": response_text,
                "tool_calls": result.get("tool_calls", []),
            }]
            self.conversation_memory.add_turn(task, plan, agents_data, response_text)
            return {"final_answer": response_text, "sub_agent_results": {agent.id: response_text}}

        sub_tasks = plan.get("sub_tasks", [])[: self.max_agents]
        agents_data, results = self._run_agents_need_based(sub_tasks)

        self.action_tracker.on_aggregate(task)
        final_answer = self._aggregate(task, results)
        self.conversation_memory.add_turn(task, plan, agents_data, final_answer)
        return {"final_answer": final_answer, "sub_agent_results": results}

    def _aggregate(self, original_task: str, results: dict) -> str:
        if not results:
            return "No results to aggregate."
        combined = "\n\n".join(
            f"[{agent_id}]\n{output.get('response', str(output))}"
            for agent_id, output in results.items()
        )
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
