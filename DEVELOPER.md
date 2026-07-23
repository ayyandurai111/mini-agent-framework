# Mini Agent Framework — Developer Documentation

**Version:** 0.4.1  
**Package:** `mini-agent-framework`  
**Repository:** https://github.com/ayyandurai111/mini-agent-framework

---

## Table of Contents

1. [Architecture Overview](#1-architecture-overview)
2. [Core Components](#2-core-components)
   - 2.1 [Orchestrator](#21-orchestrator)
   - 2.2 [Agent](#22-agent)
   - 2.3 [Tool Loop](#23-tool-loop)
3. [Tool System](#3-tool-system)
   - 3.1 [Tool Class](#31-tool-class)
   - 3.2 [ToolRegistry](#32-toolregistry)
   - 3.3 [Built-in Tools](#33-built-in-tools)
4. [Skill System](#4-skill-system)
   - 4.1 [Skill Class](#41-skill-class)
   - 4.2 [SkillRegistry](#42-skillregistry)
   - 4.3 [Skill Matching](#43-skill-matching)
   - 4.4 [Bundled Skills](#44-bundled-skills)
5. [LLM Provider System](#5-llm-provider-system)
   - 5.1 [BaseLLMProvider](#51-basellmprovider)
   - 5.2 [NvidiaProvider](#52-nvidiaprovider)
   - 5.3 [Custom Providers](#53-custom-providers)
6. [Memory System](#6-memory-system)
   - 6.1 [ConversationMemory](#61-conversationmemory)
   - 6.2 [LongTermMemory](#62-longtermmemory)
   - 6.3 [Memory Compression](#63-memory-compression)
7. [Session Management](#7-session-management)
8. [Event & Action Tracking](#8-event--action-tracking)
9. [Tool Approval System](#9-tool-approval-system)
10. [Orchestrator Prompts](#10-orchestrator-prompts)
11. [Configuration & Settings](#11-configuration--settings)
12. [Extending the Framework](#12-extending-the-framework)
    - 12.1 [Custom Tools](#121-custom-tools)
    - 12.2 [Custom Skills](#122-custom-skills)
    - 12.3 [Custom LLM Providers](#123-custom-llm-providers)
    - 12.4 [Custom Approval Callbacks](#124-custom-approval-callbacks)
    - 12.5 [Custom Event Handlers](#125-custom-event-handlers)
13. [Internals Deep Dive](#13-internals-deep-dive)
    - 13.1 [How `run()` Works Step by Step](#131-how-run-works-step-by-step)
    - 13.2 [How `chat()` Works](#132-how-chat-works)
    - 13.3 [Dependency Resolution & Parallel Execution](#133-dependency-resolution--parallel-execution)
    - 13.4 [Tool Loop Protocol](#134-tool-loop-protocol)
    - 13.5 [Memory Summarization Pipeline](#135-memory-summarization-pipeline)
14. [Development Guide](#14-development-guide)
    - 14.1 [Setup](#141-setup)
    - 14.2 [Building & Packaging](#142-building--packaging)
    - 14.3 [Testing](#143-testing)

---

## 1. Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                      Orchestrator                           │
│  ┌──────────┐  ┌──────────┐  ┌──────────────────────────┐  │
│  │ ToolReg.  │  │ SkillReg.│  │   SessionManager / Mem   │  │
│  └──────────┘  └──────────┘  └──────────────────────────┘  │
│                                                             │
│  ┌──────────────────────────────────────────────────┐      │
│  │            Planning (LLM)                         │      │
│  │  Task → single-agent? or multi-agent plan?       │      │
│  └──────────────────────────────────────────────────┘      │
│                                                             │
│  ┌──────────────────────────────────────────────────┐      │
│  │  Execution (ThreadPoolExecutor, dependency-aware) │      │
│  │  ┌──────┐  ┌──────┐  ┌──────┐                      │      │
│  │  │Agent0│  │Agent1│  │Agent2│  → parallel levels    │      │
│  │  └──────┘  └──────┘  └──────┘                      │      │
│  └──────────────────────────────────────────────────┘      │
│                                                             │
│  ┌──────────────────────────────────────────────────┐      │
│  │  Aggregation (LLM merges all agent outputs)       │      │
│  └──────────────────────────────────────────────────┘      │
└─────────────────────────────────────────────────────────────┘
```

### Key Design Decisions

| Decision | Rationale |
|----------|-----------|
| **No fixed agent pool** | Agents are created on-the-fly per task, avoiding idle resource waste |
| **LLM-based planning** | The orchestrator LLM decomposes tasks dynamically rather than using fixed DAGs |
| **JSON-only agent protocol** | Agents communicate via strict JSON — no natural language parsing needed for tool calls |
| **Parallel execution** | Sub-tasks with satisfied dependencies run concurrently via `ThreadPoolExecutor` |
| **ReAct tool loop** | Each agent uses a ReAct-style loop (Reason → Act → Observe) with JSON structured outputs |
| **Markdown skills** | Skills are plain `.md` files — non-developers can author domain knowledge |

### Module Layout

```
src/mini_agent/
├── __init__.py              # Public API exports
├── cli.py                   # CLI entry points (browser install)
├── config/
│   └── settings.py          # Global tunables (agent limits, turn counts)
├── core/
│   ├── orchestrator.py      # Central controller: plan → spawn → execute → aggregate
│   ├── agent.py             # Worker agent that runs one sub-task
│   ├── tool_loop.py         # ReAct loop: LLM ↔ tool_call ↔ result ↔ final_answer
│   ├── session_manager.py   # Named multi-turn sessions with persistence
│   ├── memory/
│   │   ├── conversation.py  # Turn-based conversation memory (JSON persisted)
│   │   └── long_term_memory.py  # Summaries + extracted user rules
│   └── utils/
│       ├── action_tracker.py # Event system: plan, agent_start, tool_call, etc.
│       ├── approval.py       # Built-in approval callbacks (cli, auto-approve, auto-reject)
│       └── json_utils.py     # JSON parsing with markdown fence stripping
├── llm/
│   └── base.py              # Abstract base: generate_stream() required, generate() derived
├── providers/
│   └── nvidia_provider.py   # NVIDIA NIM provider (OpenAI-compatible)
├── prompts/
│   ├── orchestrator_prompt.py  # System prompt for the planner LLM
│   └── prompt_builder.py       # Builds agent system prompts (role + tools + memory + skills)
├── registry/
│   ├── tools.py             # Tool dataclass + ToolRegistry
│   └── builtin/             # Ready-made tool categories
│       ├── file_tools.py    # read/write/append/list/delete files
│       ├── web_tools.py     # search/fetch/scrape/download
│       ├── math_tools.py    # calculator, uuid, random, word count
│       ├── data_tools.py    # JSON reading
│       ├── system_tools.py  # datetime, cwd
│       └── bash_tool.py     # shell command execution
└── skills/
    ├── __init__.py          # Skill dataclass + SkillRegistry + file loaders
    ├── builtin.py           # Auto-discovers bundled skills
    ├── developer/developer.md
    ├── code-review/code-review.md
    └── system-design-planning/system-design-planning.md
```

---

## 2. Core Components

### 2.1 Orchestrator

**File:** `src/mini_agent/core/orchestrator.py`

The `Orchestrator` is the central controller of the entire framework. It has four responsibilities:

1. **Planning** — Uses an LLM to decide whether a task needs sub-agents or can be answered directly
2. **Spawning** — Creates `Agent` instances at runtime, each with a subset of tools matched to capability names
3. **Execution** — Runs spawned agents in dependency-respecting parallel levels
4. **Aggregation** — Merges all agent outputs into one final answer using a second LLM call

#### Constructor

```python
Orchestrator(
    llm_provider: BaseLLMProvider,        # Required — the LLM backend
    max_agents: int = MAX_AGENTS,          # Max parallel sub-agents (default 5)
    approval_callback: Callable | None,    # Gates tool execution
    memory_file: str | None,               # Path to persistent JSON memory
    action_tracker: ActionTracker | None,  # Event system
    session_manager: SessionManager | None # Multi-session support
)
```

#### Key Methods

| Method | Description |
|--------|-------------|
| `register_tool(tool)` | Register a single `Tool` |
| `register_tools(tools)` | Register a list of `Tool` objects |
| `register_skill(skill)` | Register a single `Skill` |
| `register_skills(skills)` | Register a list of `Skill` objects |
| `load_skills_from_dir(directory)` | Load all `.md` files from a directory as skills |
| `run(task, session_id)` | Execute a task (single-agent or multi-agent), returns `{"final_answer": str, "sub_agent_results": dict}` |
| `chat(message, session_id)` | Conversational mode — streams tokens to console, returns full response string |

#### Internal Methods

| Method | Description |
|--------|-------------|
| `_plan(task, session_memory)` | Calls the LLM with the orchestrator prompt to produce a plan dict |
| `spawn_agent(role, instructions, ...)` | Creates and registers an `Agent` with matched tools/skills |
| `_run_agents_need_based(sub_tasks)` | Executes sub-tasks with dependency resolution and `ThreadPoolExecutor` parallelism |
| `_aggregate(task, results)` | Merges agent outputs into one answer via LLM |
| `_get_memory(session_id)` | Resolves the correct memory context from session or default |

### 2.2 Agent

**File:** `src/mini_agent/core/agent.py`

An `Agent` is a worker spawned by the `Orchestrator` to execute exactly one sub-task. It is a lightweight wrapper around the tool loop.

```python
Agent(
    role: str,                    # e.g. "researcher", "developer"
    instructions: str,            # The sub-task it must complete
    llm_provider: BaseLLMProvider,
    tools: list[Tool],            # Subset of tools matched to capability names
    depth: int = 0,               # Recursion depth (for nested agent spawning)
    spawn_callback: Callable,     # Reference to orchestrator.spawn_agent
    approval_callback: Callable,  # For gated tool execution
    session_memory: str,          # Dependency results injected as context
    action_tracker: ActionTracker,
    skills_context: str           # Matched skill content injected into prompt
)
```

The `run()` method:
1. Builds the system prompt via `prompt_builder.build_agent_system_prompt()`
2. Enters the tool loop (`run_with_tools`)
3. Returns `{"response": str, "tool_calls": list[dict]}`

### 2.3 Tool Loop

**File:** `src/mini_agent/core/tool_loop.py`

The tool loop implements a ReAct (Reasoning + Acting) pattern where the LLM responds with JSON on every turn. This is the core execution engine used by both worker agents and the orchestrator planner.

```python
run_with_tools(
    llm_provider: BaseLLMProvider,
    system_prompt: str,
    task: str,
    tools: list[Tool],
    max_iterations: int = 5,
    approval_callback: Callable | None,
    action_tracker: ActionTracker,
    agent_id: str,
    exit_keys: str | list[str] = "final_answer",
    return_parsed: bool = False,
    tool_history: list = None
) -> str | dict
```

**Protocol:** The LLM must respond with exactly one JSON object per turn:

```json
// Tool call
{"tool_call": "tool_name", "arguments": {"param": "value"}}

// Final answer
{"final_answer": "complete answer here"}
```

The loop:
1. Sends the system prompt + task to the LLM
2. Parses the JSON response
3. If it contains an `exit_key` (e.g. `final_answer`), returns that value
4. If it contains `tool_call`, executes the tool, appends the result to the transcript, and loops
5. If `max_iterations` is reached, prompts the user for continuation, or returns a timeout message

---

## 3. Tool System

### 3.1 Tool Class

**File:** `src/mini_agent/registry/tools.py`

```python
@dataclass
class Tool:
    name: str                    # Unique tool name
    description: str             # LLM-facing description of what it does
    func: Callable               # The Python function to execute
    parameters: dict | None      # Auto-detected from function signature if omitted
    validator: Callable | None   # Input validator (returns bool)
    on_error: Callable | None    # Error handler (returns fallback string)
    requires_approval: bool      # Gates execution behind approval callback
    read_only: bool              # Available during planning phase (default True)
```

#### Auto-detection of Parameters

If `parameters` is `None`, `__post_init__` calls `_auto_detect_parameters()` which uses `inspect.signature()` to extract parameter names and type annotations:

```python
def my_tool(path: str, verbose: bool = False) -> str: ...
# → {"path": "str", "verbose": "bool (optional, default=False)"}
```

#### Tool Execution

```python
def run(self, *args, **kwargs):
    # 1. Validate if validator is set
    # 2. Execute self.func(*args, **kwargs)
    # 3. On exception: call self.on_error(exc) if set, else re-raise
```

### 3.2 ToolRegistry

```python
class ToolRegistry:
    def register(tool: Tool)      # Adds to internal dict
    def unregister(name: str)     # Removes by name
    def get(name: str) -> Tool    # Lookup by name
    def match(names: list[str])   # Returns list of Tool matching capability names
    def list_available()          # Returns all registered tool names
    def get_read_only()           # Returns names of tools with read_only=True
```

### 3.3 Built-in Tools

| Category | Tools | Source |
|----------|-------|--------|
| **FILE_TOOLS** | `read_text_file`, `write_text_file`, `append_text_file`, `list_directory`, `file_exists`, `delete_file` | `file_tools.py` |
| **WEB_TOOLS** | `web_search`, `fetch_url`, `browse_url`, `scrape_webpage`, `download_file` | `web_tools.py` |
| **DATA_TOOLS** | `read_json` | `data_tools.py` |
| **MATH_TOOLS** | `calculator`, `generate_uuid`, `random_number`, `word_count` | `math_tools.py` |
| **SYSTEM_TOOLS** | `get_current_datetime`, `get_current_working_directory` | `system_tools.py` |
| **BASH_TOOL** | `bash` (shell command execution) | `bash_tool.py` |
| **BROWSER_TOOLS** | `browser_open`, `browser_click`, `browser_fill`, etc. (opt-in, requires Playwright) | `browser_tools.py` |

**Important design notes on built-in tools:**

- **`web_search`** uses DuckDuckGo's Instant Answer API (no API key needed), not a full web index
- **`fetch_url`** uses `trafilatura` for content extraction with a fallback to raw HTML
- **`calculator`** uses AST-based safe evaluation — no `eval()` to prevent code injection
- **`bash`** gives full OS access and defaults to `requires_approval=True, read_only=False`
- **Write/delete tools** default to `requires_approval=True` since they modify the filesystem
- **Browser tools** are lazily imported to keep the core lightweight

---

## 4. Skill System

### 4.1 Skill Class

**File:** `src/mini_agent/skills/__init__.py`

```python
@dataclass
class Skill:
    name: str              # Unique identifier (kebab-case)
    description: str       # Short description for keyword matching
    file_path: str = ""    # Path to the .md file with full content
```

### 4.2 SkillRegistry

```python
class SkillRegistry:
    def register(skill: Skill)          # Adds to internal dict
    def unregister(name: str)           # Removes by name
    def get(name: str) -> Skill | None  # Lookup
    def match(task_text: str) -> list[Skill]  # Keyword overlap matching
    def list() -> list[str]             # All skill names
    def load_from_file(path) -> Skill   # Parse a .md skill file
    def load_from_dir(directory)        # Load all skills from a directory tree
```

### 4.3 Skill Injection

Skills are **not** keyword-matched to tasks. The **planner LLM** decides which skill (if any) a worker needs, via the `skill` field in the plan JSON — same way it selects tools via `required_capabilities`. Only the planned skill is injected into the agent's system prompt.

```python
# Planner output for single-agent
{"needs_sub_agents": false, "skill": "developer", "required_capabilities": ["write_text_file"]}

# Planner output for multi-agent (per sub-task)
{"skill": "code-review", "depends_on": [0]}
```

The `SkillRegistry.match()` method is still available with stop-word filtering and a ≥2 word overlap threshold, but it is no longer used by the Orchestrator.

### 4.4 Skill File Format

Skills use Markdown with optional YAML frontmatter:

```markdown
---
name: skill-name
description: Short description for matching
---

# Skill Title

Full workflow content here...
```

The frontmatter is parsed by `_parse_frontmatter()` which handles both:
- YAML-style (`key: value`)
- JSON-style (`{"key": "value"}`)

If no frontmatter is present, the skill name defaults to the filename (without `.md`) and the description is the first 200 characters of content.

---

## 5. LLM Provider System

### 5.1 BaseLLMProvider

**File:** `src/mini_agent/llm/base.py`

```python
class BaseLLMProvider(ABC):
    def generate(self, system_prompt: str, user_message: str) -> str:
        # Default implementation: accumulates tokens from generate_stream()
        return "".join(self.generate_stream(system_prompt, user_message))

    @abstractmethod
    def generate_stream(self, system_prompt: str, user_message: str):
        # Must be a generator yielding str tokens
        raise NotImplementedError
```

Key contract:
- You **must** implement `generate_stream()` — it should be a generator that yields tokens one at a time
- `generate()` is provided automatically and is used by the tool loop for non-streaming calls
- The tool loop uses `generate()` for agent execution (not streaming)
- `Orchestrator.chat()` uses `generate_stream()` for live token output

### 5.2 NvidiaProvider

**File:** `src/mini_agent/providers/nvidia_provider.py`

Connects to [NVIDIA NIM](https://integrate.api.nvidia.com/v1) using the OpenAI SDK.

```python
NvidiaProvider(
    api_key: str = None,                        # Falls back to NVIDIA_API_KEY env var
    model: str = "deepseek-ai/deepseek-v4-flash",
    temperature: float = 0.7,
    top_p: float = 0.95,
    max_tokens: int = 4096,
    base_url: str = "https://integrate.api.nvidia.com/v1",
    max_retries: int = 5                        # Exponential backoff: 5s, 10s, 20s, 40s
)
```

**Recommended models** (warns if not in list, still works):
- `deepseek-ai/deepseek-v4-flash` (default)
- `meta/llama-3.3-70b-instruct`
- `mistralai/mistral-large-2-instruct`
- `nvidia/llama-3.1-nemotron-70b-instruct`
- `qwen/qwen2.5-72b-instruct`
- `google/gemma-2-27b-it`
- `microsoft/phi-4`
- `deepseek-ai/deepseek-v4-pro`
- `nvidia/nemotron-3-ultra-550b-a55b`
- and more in `RECOMMENDED_MODELS` list

Any model available in the NVIDIA catalog can be used — unknown models print a warning but work normally.

**Error types:**
- `AuthenticationErrorWrapper` — invalid/missing API key
- `RateLimitErrorWrapper` — rate limited after retries with exponential backoff
- `ConnectionErrorWrapper` — network connectivity issues
- `NvidiaProviderError` — generic provider error

**Retry behavior:**
- RateLimitError / APIStatusError (429): sleeps `5 * 2^attempt` seconds between retries (5s, 10s, 20s, 40s)
- ConnectionError/APIError: sleeps 1 second between retries
- Other exceptions: raised immediately

### 5.3 Custom Providers

To use any other LLM (OpenAI, Anthropic, Ollama, Groq, etc.), implement `BaseLLMProvider`:

```python
from mini_agent import BaseLLMProvider

class OpenAILikeProvider(BaseLLMProvider):
    def __init__(self, api_key: str, model: str = "gpt-4", base_url: str = None):
        self.client = OpenAI(api_key=api_key, base_url=base_url)
        self.model = model

    def generate_stream(self, system_prompt: str, user_message: str):
        stream = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message},
            ],
            stream=True,
        )
        for chunk in stream:
            if chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content
```

---

## 6. Memory System

The memory system has two layers — short-term `ConversationMemory` and long-term `LongTermMemory`.

### 6.1 ConversationMemory

**File:** `src/mini_agent/core/memory/conversation.py`

Stores conversation turns as a list of formatted strings, persisted as JSON.

```python
ConversationMemory(
    max_turns: int = MEMORY_MAX_TURNS,     # 5 by default (0 = unlimited)
    persist_file: str = MEMORY_PERSIST_FILE,
    summarize_callback: Callable = None
)
```

**Key methods:**

| Method | Description |
|--------|-------------|
| `add_turn(user_input, plan, agents, result)` | Formats and appends a turn, trims to `max_turns`, saves to disk |
| `get_context()` | Returns compressed context string for agent prompts |
| `inject_long_term(rules_text, summary_text)` | Injects LTM data for context building |
| `search(query)` | Full-text search across turns |
| `raw_turns()` | Returns raw list of turn strings |
| `clear()` | Resets all turns |

**Turn format** (from `_format()`):

```
=== USER ===
user input text

=== PLAN ===
direct_agent

=== AGENT[direct]: direct_agent ===
[agent response text]
  >> tool_name(param=value) -> result text

=== RESULT ===
final result text
```

### 6.2 LongTermMemory

**File:** `src/mini_agent/core/memory/long_term_memory.py`

Persistent long-term storage for a session. Contains summaries and extracted user rules.

```python
LongTermMemory(persist_file: str)
```

**Methods:**

| Method | Description |
|--------|-------------|
| `add_summary(turn_range, summary)` | Store a summary for a range of turns |
| `get_latest_summary()` | Returns the most recent summary |
| `add_rules(new_rules, source_turn)` | Adds extracted user rules (deduplicated) |
| `get_rules_text()` | Returns all rules as a formatted string |
| `search_summaries(query)` | Search across summaries |
| `search_rules(query)` | Search across rules |

### 6.3 Memory Compression

When building context for agent prompts, `ConversationMemory._build_compressed_context()` applies a **token budget** (default: 4000 tokens via `MAX_CONTEXT_TOKENS`) with this priority:

1. **User rules** (highest priority) — always included first
2. **Latest summary** — included if budget permits
3. **Recent turns** — newest first, up to `MEMORY_CONTEXT_TURNS` (default 2), filling remaining budget

Token counting uses `tiktoken` (cl100k_base encoding) with a fallback to `len(text) // 4`.

---

## 7. Session Management

**File:** `src/mini_agent/core/session_manager.py`

```python
SessionManager(sessions_dir: str | None = None)
```

Sessions are stored as individual JSON files in a platform-appropriate directory:
- **Windows:** `%APPDATA%/mini_agent/sessions/`
- **macOS:** `~/Library/Application Support/mini_agent/sessions/`
- **Linux:** `~/.config/mini_agent/sessions/`

An `index.json` manifest tracks metadata.

| Method | Description |
|--------|-------------|
| `create_session(name)` | Creates a new session with UUID, returns metadata dict |
| `list_sessions()` | Returns list of all session metadata (with live turn counts) |
| `get_session(id)` | Returns `ConversationMemory` for the session (loaded on demand) |
| `get_long_term_memory(id)` | Returns `LongTermMemory` for the session |
| `delete_session(id)` | Removes session file + index entry + LTM file |
| `rename_session(id, name)` | Updates display name |
| `get_or_create_active()` | Returns active session, creates one if none exists |
| `touch_session(id)` | Updates turn count and timestamp |

**Memory resolution logic** in `Orchestrator._get_memory()`:

```
if session_manager:
    if session_id → get that session's memory
    else → get_or_create_active()
    also → get_long_term_memory(session_id)
else:
    → default ConversationMemory (possibly file-persisted)
```

---

## 8. Event & Action Tracking

**File:** `src/mini_agent/core/utils/action_tracker.py`

```python
class ActionTracker:
    def __init__(self, on_event: Callable[[str, dict], None] | None):
        self._custom_callback = on_event
```

**Event types:**

| Event | `data` dict keys | Trigger |
|-------|-------------------|---------|
| `plan` | `task`, `needs_sub_agents`, `sub_tasks`, `tools_count`, `skills_available`, `required_capabilities` | After LLM planning |
| `agent_start` | `agent_id`, `role`, `instructions`, `capabilities`, `skills` | When a worker agent is spawned |
| `agent_end` | `agent_id`, `role`, `result` | When an agent completes or fails |
| `tool_call` | `agent_id`, `tool`, `arguments`, `iteration`, `total` | Before tool execution |
| `tool_result` | `agent_id`, `tool`, `result` | After tool returns |
| `token` | `token`, `agent_id` | Each streamed token in chat mode |
| `aggregate` | `task` | When Orchestrator begins merging results |
| `research` | `tool`, `arguments`, `result` | Planning-phase research actions |

The default handler `console_event_logger` renders events with Unicode box-drawing to stderr:

```
╔═══ PLAN ═══════════════════════════
║  Decision : multi-agent (2 sub-tasks)
║  Task #0 : researcher  [web_search]
║  Task #1 : developer  [write_text_file, bash]  ← after #0
╚════════════════════════════════════

    ┌══ WORKER: researcher ═══════════════════════════┐
    │  Search for latest AI frameworks                 │
    │  Tools: web_search                               │
    └══════════════════════════════════════════════════┘
      ┏  web_search(query=AI trends 2026)
      ┃  → Found 3 major frameworks...
    ┌══ WORKER: developer ═══════════════════════════┐
    │  Write code based on research                   │
    │  Tools: write_text_file, bash                   │
    │  Skills: developer                              │
    └══════════════════════════════════════════════════┘
      ┃  1/5  ⚙ write_text_file(path=output.py, content=...)
      ┃        → Wrote 500 characters to output.py

╔═══ AGGREGATOR ════════════════════════════════
║  Merging agent outputs...
╚═══════════════════════════════════════════════
```

---

## 9. Tool Approval System

**File:** `src/mini_agent/core/utils/approval.py`

An `approval_callback` is a function `(tool_name: str, arguments: dict) -> bool`. When a tool has `requires_approval=True`, the tool loop calls this callback before execution.

**Resolution logic:**

```
if tool.requires_approval:
    if approval_callback is None → run tool (fully autonomous)
    if approval_callback returns True → run tool
    if approval_callback returns False → skip, inject rejection message
```

**Built-in callbacks:**

| Callback | Behavior |
|----------|----------|
| `cli_approval_callback` | Prompts `[y/N]` on terminal, blocks for input |
| `auto_approve_callback` | Always returns `True` (logging/audit mode) |
| `auto_reject_callback` | Always returns `False` (dry-run / read-only mode) |

When rejected, the LLM receives this message:
> "The user did not approve this action. Do not repeat it — choose a different approach, or explain why it was needed in your final answer."

---

## 10. Orchestrator Prompts

### 10.1 Planning Prompt

**File:** `src/mini_agent/prompts/orchestrator_prompt.py`

The orchestrator LLM receives a detailed system prompt that defines:

1. **Role** — Task Orchestrator with read-only tools
2. **Research Phase** — Use read-only tools for fact-finding before planning
3. **Two Modes:**
   - **Direct Answer** — `{"final_answer": "..."}` for simple questions
   - **Plan** — `{"needs_sub_agents": bool, "required_capabilities": [...], "sub_tasks": [...]}` for complex tasks
4. **Output contract** — Strict JSON schema for the plan
5. **Examples** — 5 worked examples covering each mode

The prompt is dynamically extended at runtime with:
- Current tool list (names + descriptions)
- Current skill list (names + descriptions)
- Session memory context (if available)

### 10.2 Agent Prompt Builder

**File:** `src/mini_agent/prompts/prompt_builder.py`

Builds the system prompt for each worker agent with:

1. **Role header** — Identity as a specialized worker in a multi-agent system
2. **Skills block** — Matched skill content (if any)
3. **Memory block** — Session context / dependency results (if any)
4. **Task instructions** — The sub-task to complete
5. **Tools block** — Available tools with descriptions
6. **Output contract** — JSON schema for tool calls and final answer
7. **Rules** — Output discipline, tool usage guidelines, anti-hallucination rules

---

## 11. Configuration & Settings

**File:** `src/mini_agent/config/settings.py`

| Setting | Default | Description |
|---------|---------|-------------|
| `MAX_AGENTS` | 5 | Maximum parallel sub-agents per task |
| `MAX_RECURSION_DEPTH` | 2 | Maximum nested agent spawn depth |
| `MAX_TOOL_ITERATIONS` | 5 | Maximum tool calls per agent before forced exit |
| `MEMORY_MAX_TURNS` | 5 | Turns retained in non-session memory |
| `SESSION_MAX_TURNS` | 0 | Turns per session (0 = unlimited) |
| `MEMORY_CONTEXT_TURNS` | 2 | Recent turns included in agent prompt |
| `MAX_CONTEXT_TOKENS` | 4000 | Token budget for compressed context |
| `SUMMARIZE_EVERY_N_TURNS` | 5 | LTM summarization frequency |

All settings are module-level variables — override by importing and assigning before creating the `Orchestrator`:

```python
from mini_agent.config.settings import MAX_AGENTS, MAX_TOOL_ITERATIONS
MAX_AGENTS = 10
MAX_TOOL_ITERATIONS = 8
```

**Platform-specific paths** for session persistence:

| Platform | Path |
|----------|------|
| Windows | `%APPDATA%/mini_agent/sessions/` |
| macOS | `~/Library/Application Support/mini_agent/sessions/` |
| Linux | `~/.config/mini_agent/sessions/` |

---

## 12. Extending the Framework

### 12.1 Custom Tools

Wrap any Python function as a `Tool`:

```python
from mini_agent import Tool

def analyze_sentiment(text: str, language: str = "en") -> str:
    """Returns 'positive', 'negative', or 'neutral'."""
    # ... implementation ...
    return "positive"

tool = Tool(
    name="analyze_sentiment",
    description="Analyze the sentiment of a text string",
    func=analyze_sentiment,
    # parameters auto-detected: {"text": "str", "language": "str (optional, default=en)"}
    requires_approval=False,
    read_only=True,
)
```

**With validator and error handler:**

```python
def validate_path(path: str) -> bool:
    return not path.startswith("..")  # prevent directory traversal

def on_file_error(exc: Exception) -> str:
    return f"File operation failed: {exc}"

safe_tool = Tool(
    name="safe_read",
    description="Read a file safely",
    func=read_text_file,
    validator=validate_path,
    on_error=on_file_error,
)
```

### 12.2 Custom Skills

**From a Markdown file:**

```markdown
---
name: data-analysis
description: Analyze datasets, generate statistics, and create visualizations
---

# Data Analysis Workflow

1. Load the dataset using available tools
2. Clean and preprocess...
3. Generate summary statistics...
4. Create visualizations...
```

```python
from mini_agent import Skill
from mini_agent.skills import load_skill_from_file

skill = load_skill_from_file("skills/data-analysis/data-analysis.md")
orch.register_skill(skill)
```

**Programmatically:**

```python
skill = Skill(
    name="data-analysis",
    description="Analyze datasets and create visualizations",
    file_path="skills/data-analysis/data-analysis.md",
)
orch.register_skill(skill)
```

### 12.3 Custom LLM Providers

```python
from mini_agent import BaseLLMProvider

class AnthropicProvider(BaseLLMProvider):
    def __init__(self, api_key: str, model: str = "claude-3-opus-20240229"):
        import anthropic
        self.client = anthropic.Anthropic(api_key=api_key)
        self.model = model

    def generate_stream(self, system_prompt: str, user_message: str):
        with self.client.messages.stream(
            model=self.model,
            system=system_prompt,
            messages=[{"role": "user", "content": user_message}],
            max_tokens=4096,
        ) as stream:
            for text in stream.text_stream:
                yield text
```

### 12.4 Custom Approval Callbacks

```python
def audit_approval(tool_name: str, arguments: dict) -> bool:
    log_audit(tool_name, arguments)
    if tool_name == "bash" and "rm -rf" in arguments.get("command", ""):
        print("⚠ Dangerous command blocked")
        return False
    return True

orch = Orchestrator(llm, approval_callback=audit_approval)
```

### 12.5 Custom Event Handlers

```python
def json_logger(event_type: str, data: dict):
    import json, sys
    print(json.dumps({"event": event_type, **data}), file=sys.stderr)

tracker = ActionTracker(on_event=json_logger)
orch = Orchestrator(llm, action_tracker=tracker)
```

---

## 13. Internals Deep Dive

### 13.1 How `run()` Works Step by Step

```
Task: "Research AI trends and write a summary"
           │
           ▼
   1. Orchestrator.run(task)
           │
           ▼
   2. _get_memory(session_id)
      → Resolve ConversationMemory + LongTermMemory
      → Inject LTM rules/summary into memory context
           │
           ▼
   3. _plan(task, session_memory)
      → Build system prompt with tools + skills
      → Call LLM (with read-only tools for research)
      → Parse JSON response
      → Emit "plan" event
           │
           ▼
   4. Decision point:
      ┌─────────────────┐                    ┌─────────────────┐
      │ "final_answer"  │                    │ "needs_sub_     │
      │ in response     │                    │ agents": true   │
       └────────┬────────┘                    └────────┬────────┘
                │                                      │
                ▼                                      ▼
       Return direct answer                    5. Read plan.skill field
                                                → Load single skill if set
                                                → Build skills_context
                                                         │
                                                         ▼
                                               6. _run_agents_need_based(sub_tasks)
                                              → Build dependency graph
                                              → Resolve execution levels
                                              → For each level (parallel):
                                                  spawn_agent() for each sub-task
                                                  ThreadPoolExecutor.submit(agent.run)
                                                  as_completed() → collect results
                                              → Emit agent_start/agent_end events
                                                    │
                                                    ▼
                                           7. _aggregate(task, results)
                                              → Combine all agent outputs
                                              → Call LLM with aggregation prompt
                                              → Emit "aggregate" event
                                                    │
                                                    ▼
                                           8. memory.add_turn(task, plan, agents, answer)
                                           9. Return {"final_answer": ..., "sub_agent_results": ...}
```

### 13.2 How `chat()` Works

```
chat("What is machine learning?")
  │
  ▼
1. Resolve memory (session or default)
2. Inject LTM rules/summary
3. Build system prompt: "You are a helpful AI assistant..."
4. Enter generate_stream() loop:
   for token in llm_provider.generate_stream(system_prompt, message):
       print(token, end="")  # live console output
       action_tracker.on_token(token)
5. memory.add_turn(message, plan={}, agents=[], response)
6. Return full response string
```

`chat()` is strictly single-turn, single-LLM — no agents, no tools, no planning. It is designed for conversational Q&A where streaming matters.

### 13.3 Dependency Resolution & Parallel Execution

**File:** `src/mini_agent/core/orchestrator.py:_run_agents_need_based()`

The dependency resolution algorithm:

```python
sub_tasks = [
    {"role": "researcher", "depends_on": []},           # Level 0
    {"role": "writer", "depends_on": [0]},              # Level 1
    {"role": "reviewer", "depends_on": [0, 1]},         # Level 2
]
```

1. Find all tasks with satisfied dependencies → Level 0
2. Remove executed tasks from dependency sets
3. Repeat until all tasks are assigned to levels
4. Raises `RuntimeError` on circular dependencies

Each level runs in parallel via `ThreadPoolExecutor`:

```python
for level in levels:
    with ThreadPoolExecutor(max_workers=min(len(level), self.max_agents)) as executor:
        future_to_idx = {executor.submit(agent.run): idx for idx in level}
        for future in as_completed(future_to_idx):
            result = future.result()
```

**Memory injection for dependent agents:** If `sub_task.memory == True`, the agent receives dependency results injected as `=== DEPENDENCY RESULTS ===` in its session memory context.

### 13.4 Tool Loop Protocol

The tool loop (`run_with_tools`) implements a strict JSON protocol:

**Turn structure:**

```
Turn 1:
  User: system_prompt + task
  LLM: {"tool_call": "web_search", "arguments": {"query": "AI trends 2026"}}
  System: "You called web_search with arguments {...}.\nResult: Found 3 trends..."
  
Turn 2:
  System: transcript (accumulated)
  LLM: {"tool_call": "write_text_file", "arguments": {"path": "summary.md", "content": "..."}}
  System: "You called write_text_file with arguments {...}.\nResult: Wrote 500 chars..."

Turn 3:
  System: transcript
  LLM: {"final_answer": "Research complete. Summary saved to summary.md."}
  → returns "Research complete. Summary saved to summary.md."
```

**Edge case — tool not found:**
```
Result: Error: tool 'non_existent_tool' is not available to you.
```

**Edge case — max iterations reached:**
```
(Reached 5 tool calls. Continue? y/n:
```
User can type `y` to reset iteration counter, `n` to return a timeout message.

### 13.5 Memory Summarization Pipeline

Every `SUMMARIZE_EVERY_N_TURNS` (default 5) turns, `Orchestrator._summarize_memory()` is called:

1. Collect new turns since last summarization
2. Call LLM with summarization prompt:
   ```
   Analyze these turns and produce:
   1. A concise summary (key decisions, results, topics)
   2. A list of user rules extracted ("The user...")
   Output JSON: {"summary": "...", "rules": [{"rule": "...", "category": "preference|role|constraint|general"}]}
   ```
3. Store summary in `LongTermMemory.add_summary()`
4. Store extracted rules in `LongTermMemory.add_rules()` (deduplicated)
5. Update `inject_long_term()` so the compressed context includes the latest summary and rules

---

## 14. Development Guide

### 14.1 Setup

```bash
git clone https://github.com/ayyandurai111/mini-agent-framework.git
cd mini-agent-framework

# Editable install (core)
pip install -e .

# With browser automation
pip install -e .[browser]
mini-agent-install-browser

# Bring your own API key
export NVIDIA_API_KEY="nvapi-..."
```

### 14.2 Building & Packaging

```bash
# Build distribution packages
pip install build
python -m build

# Publish to PyPI
pip install twine
twine upload dist/*
```

The `pyproject.toml` configuration:
- **Build system:** `setuptools >=64`
- **Package discovery:** `src/` directory, includes `mini_agent.*`
- **Package data:** Markdown skill files are included via `tool.setuptools.package-data`
- **Python requirement:** `>=3.11`

### 14.3 Testing

Configured for `pytest` (see `[tool.pytest.ini_options]` in `pyproject.toml`):

```bash
# Run all tests
pytest

# Run with verbose output
pytest -v

# Run specific test file
pytest tests/test_orchestrator.py
```

---

## API Reference Summary

### Public API (from `mini_agent/__init__.py`)

```python
from mini_agent import (
    Orchestrator,         # Core controller
    SessionManager,       # Multi-session persistence
    Tool,                 # Tool dataclass
    Skill,                # Skill dataclass
    SkillRegistry,        # Skill management
    BaseLLMProvider,      # Abstract LLM provider
    NvidiaProvider,       # Built-in NVIDIA provider
    ActionTracker,        # Event system
    console_event_logger, # Default event formatter
)
```

### Submodule Access

```python
from mini_agent.registry.builtin import (
    BUILTIN_TOOLS, FILE_TOOLS, WEB_TOOLS, DATA_TOOLS,
    MATH_TOOLS, SYSTEM_TOOLS, BASH_TOOL, BROWSER_TOOLS, ALL_TOOLS,
    init_browser,
)

from mini_agent.skills.builtin import (
    SKILLS, CODE_REVIEW, DEVELOPER, SYSTEM_DESIGN_PLANNING,
)

from mini_agent.core.utils import (
    cli_approval_callback, auto_approve_callback, auto_reject_callback,
)

from mini_agent.config.settings import (
    MAX_AGENTS, MAX_TOOL_ITERATIONS, MAX_RECURSION_DEPTH,
    MEMORY_MAX_TURNS, SESSION_MAX_TURNS, MEMORY_CONTEXT_TURNS,
    MAX_CONTEXT_TOKENS, SUMMARIZE_EVERY_N_TURNS,
)
```
