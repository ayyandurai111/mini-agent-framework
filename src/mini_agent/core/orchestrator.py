"""
core/orchestrator.py
-----------------------
Plans tasks, spawns agents with matched tools/skills, and aggregates results.
"""

from concurrent.futures import ThreadPoolExecutor, as_completed

from ..llm.base import BaseLLMProvider
from .utils.action_tracker import ActionTracker, console_event_logger
from .agent import Agent
from .tool_loop import run_with_tools
from .utils.json_utils import try_parse_json
from .memory.conversation import ConversationMemory
from .session_manager import SessionManager
from ..registry.tools import ToolRegistry
from ..prompts.orchestrator_prompt import ORCHESTRATOR_SYSTEM_PROMPT
from ..config.settings import MAX_AGENTS, MAX_RECURSION_DEPTH, SUMMARIZE_EVERY_N_TURNS
from ..skills import Skill, SkillRegistry, read_skill_content


class Orchestrator:
    def __init__(self, llm_provider: BaseLLMProvider, max_agents: int = MAX_AGENTS,
                 approval_callback=None, memory_file: str = None,
                 action_tracker: ActionTracker = None,
                 session_manager: SessionManager = None):
        if llm_provider is None:
            raise ValueError(
                "llm_provider is required. Implement BaseLLMProvider and pass an instance."
            )
        self.llm_provider = llm_provider
        self.max_agents = max_agents
        self.tool_registry = ToolRegistry()
        self.active_agents = {}
        self.approval_callback = approval_callback
        self.action_tracker = action_tracker or ActionTracker(on_event=console_event_logger)
        self.skill_registry = SkillRegistry()
        self.session_manager = session_manager
        if session_manager:
            self.conversation_memory = None
        else:
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

    def _get_memory(self, session_id=None):
        """Resolve ConversationMemory + LongTermMemory from session or default."""
        if self.session_manager:
            if session_id:
                mem = self.session_manager.get_session(session_id)
                ltm = self.session_manager.get_long_term_memory(session_id)
                return session_id, mem, ltm
            sid, mem = self.session_manager.get_or_create_active()
            ltm = self.session_manager.get_long_term_memory(sid)
            return sid, mem, ltm
        return None, self.conversation_memory, None

    def _summarize_memory(self, memory: ConversationMemory, ltm) -> None:
        """Summarize recent turns + extract rules via LLM."""
        if ltm is None:
            return
        last_summarized = getattr(ltm, '_last_summarized_turn', 0)
        turns = memory.raw_turns()
        if len(turns) <= last_summarized:
            ltm._last_summarized_turn = len(turns)
            return
        new_turns = turns[last_summarized:]
        if not new_turns:
            return
        turn_text = "\n\n---\n\n".join(
            f"Turn {last_summarized + i + 1}:\n{t}"
            for i, t in enumerate(new_turns)
        )
        prompt = (
            "You are a memory summarization assistant. Analyze the conversation turns below "
            "and produce:\n"
            "1. A concise summary of what happened (key decisions, results, topics covered).\n"
            "2. A list of user rules extracted from the conversation — these are the user's "
            "stated preferences, role constraints, or requirements. Each rule should be "
            'a single clear sentence starting with "The user".\n\n'
            "Output format (JSON only, no other text):\n"
            '{"summary": "<concise summary>", '
            '"rules": [{"rule": "The user...", "category": "preference|role|constraint|general"}, ...]}\n\n'
            f"Turns to process:\n{turn_text}"
        )
        try:
            raw = self.llm_provider.generate(
                system_prompt="You are a memory summarization assistant.",
                user_message=prompt,
            )
            import json
            result = json.loads(raw.strip().removeprefix("```json").removesuffix("```").strip())
        except Exception:
            result = {"summary": "", "rules": []}
        summary = result.get("summary", "")
        rules = result.get("rules", [])
        if summary:
            ltm.add_summary([last_summarized, len(turns) - 1], summary)
        if rules:
            ltm.add_rules(rules, len(turns) - 1)
        ltm._last_summarized_turn = len(turns)
        rules_text = ltm.get_rules_text()
        summary_text = ltm.get_latest_summary() or ""
        memory.inject_long_term(rules_text=rules_text, summary_text=summary_text)

    def _build_chat_system_prompt(self, context: str) -> str:
        parts = [
            "You are a helpful AI assistant. Answer the user's questions "
            "conversationally. Be concise and accurate."
        ]
        if context:
            parts.append(f"\n\n## CONVERSATION HISTORY\n{context}")
        return "\n".join(parts)

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
        if skill_names:
            skill_descs = [f"  - {self.skill_registry.get(s).describe()}" for s in skill_names]
            system_prompt += "\n## SKILLS AVAILABLE\n" + "\n".join(skill_descs) + "\n"
            system_prompt += "\nOnly set 'skill' field to one of the above names. Do NOT invent skill names.\n"
        else:
            system_prompt += "\n## SKILLS AVAILABLE\n  (none registered — do NOT set 'skill' in sub_tasks)\n"

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

        for t in plan.get("sub_tasks", []):
            s = t.get("skill", "")
            if s and not self.skill_registry.get(s):
                import warnings
                warnings.warn(f"Plan referenced unknown skill '{s}' — removed")
                t["skill"] = ""

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

    def run(self, task: str, session_id: str = None) -> dict:
        self.active_agents.clear()
        sid, memory, ltm = self._get_memory(session_id)

        rules_text = ltm.get_rules_text() if ltm else ""
        summary_text = ltm.get_latest_summary() or "" if ltm else ""
        memory.inject_long_term(rules_text=rules_text, summary_text=summary_text)
        memory.set_summarize_callback(
            lambda mem: self._summarize_memory(mem, ltm) if ltm else None
        )

        plan = self._plan(task, session_memory=memory.get_context())

        if "final_answer" in plan:
            answer = plan["final_answer"]
            memory.add_turn(task, plan, [], answer)
            if self.session_manager and sid:
                self.session_manager.touch_session(sid)
            return {"final_answer": answer, "sub_agent_results": {}}

        skill_name = plan.get("skill", "")
        skills_context = ""
        if skill_name:
            skill = self.skill_registry.get(skill_name)
            if skill:
                skills_context = f"[SKILL: {skill.name}]\n{read_skill_content(skill)}"

        if not plan.get("needs_sub_agents"):
            capability_names = plan.get("required_capabilities") or self.tool_registry.get_read_only()
            agent = self.spawn_agent(
                role="direct_agent",
                instructions=f"Task: {task}",
                capability_names=capability_names,
                skills_context=skills_context,
                skill_names=[skill_name] if skill_name else [],
                session_memory=memory.get_context(),
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
            memory.add_turn(task, plan, agents_data, response_text)
            if self.session_manager and sid:
                self.session_manager.touch_session(sid)
            return {"final_answer": response_text, "sub_agent_results": {agent.id: response_text}}

        sub_tasks = plan.get("sub_tasks", [])[: self.max_agents]
        agents_data, results = self._run_agents_need_based(sub_tasks)

        self.action_tracker.on_aggregate(task)
        final_answer = self._aggregate(task, results)
        memory.add_turn(task, plan, agents_data, final_answer)
        if self.session_manager and sid:
            self.session_manager.touch_session(sid)
        return {"final_answer": final_answer, "sub_agent_results": results}

    def chat(self, message: str, session_id: str = None) -> str:
        """Streams tokens directly to console and returns the full response string.

        Usage:
            result = orch.chat("hello")  # live output, no loop needed
        """
        sid = None
        ltm = None
        if self.session_manager:
            if session_id:
                sid = session_id
                memory = self.session_manager.get_session(sid)
                ltm = self.session_manager.get_long_term_memory(sid)
            else:
                sid, memory = self.session_manager.get_or_create_active()
                ltm = self.session_manager.get_long_term_memory(sid)
        else:
            memory = self.conversation_memory

        rules_text = ltm.get_rules_text() if ltm else ""
        summary_text = ltm.get_latest_summary() or "" if ltm else ""
        memory.inject_long_term(rules_text=rules_text, summary_text=summary_text)
        memory.set_summarize_callback(
            lambda mem: self._summarize_memory(mem, ltm) if ltm else None
        )

        context = memory.get_context()
        system_prompt = self._build_chat_system_prompt(context)

        full_response = ""
        try:
            for token in self.llm_provider.generate_stream(system_prompt, message):
                print(token, end="", flush=True)
                self.action_tracker.on_token(token, agent_id="chat")
                full_response += token
        except Exception as e:
            print(f"\n[Error: {e}]")
            return ""

        print()
        memory.add_turn(message, {"needs_sub_agents": False}, [], full_response)

        if self.session_manager and sid:
            self.session_manager.touch_session(sid)

        return full_response

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
                f"Output only the final answer \u2014 no meta-commentary."
            )
            return self.llm_provider.generate(
                system_prompt="You are an Aggregator AI that merges sub-agent outputs into one coherent final answer.",
                user_message=aggregation_prompt,
            )
        except (OSError, RuntimeError, ValueError):
            return f"[Aggregation fallback \u2014 raw sub-agent results]\n\n{combined}"
