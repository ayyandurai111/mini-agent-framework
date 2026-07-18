# mini-agent-framework

**A dynamic, need-based multi-agent AI framework for Python.**  
No fixed agent pool — the Orchestrator plans the task, spawns worker agents with matched tools and skills at runtime, and aggregates their results into one coherent answer.

[![Python](https://img.shields.io/badge/python-3.11%2B-blue)](https://python.org)
[![License](https://img.shields.io/badge/license-MIT-green)](LICENSE)
[![PyPI](https://img.shields.io/pypi/v/mini-agent-framework)](https://pypi.org/project/mini-agent-framework/)

---

## Features

| Feature | Description |
|---------|-------------|
| **Dynamic Agent Spawning** | No pre-defined pool — agents are created on-the-fly per task |
| **Need-Based Planning** | LLM-powered planner decomposes tasks into sub-tasks automatically |
| **Parallel Execution** | Sub-tasks run concurrently with dependency-aware scheduling |
| **Tool System** | Built-in file, web, math, data, system, bash, and browser tools |
| **Skill System** | Domain expertise via Markdown files injected into agent prompts |
| **Session Management** | Multi-turn chat with persistent, named sessions |
| **Action Tracking** | Real-time event logging (plan, agent lifecycle, tool calls, aggregation) |
| **Tool Approval** | Gated execution with optional user approval callback |
| **Streaming** | `chat()` streams LLM tokens live to the console |
| **Custom Providers** | Extend `BaseLLMProvider` for any LLM (OpenAI, Anthropic, Ollama, etc.) |
| **Custom Tools** | Wrap any Python function as a tool with automatic parameter detection |

---

## Installation

```bash
pip install mini-agent-framework
```

### With browser automation (Playwright)

```bash
pip install mini-agent-framework[browser]
mini-agent-install-browser
```

---

## Quick Start

```python
import os
from mini_agent import Orchestrator, NvidiaProvider
from mini_agent.registry.builtin import FILE_TOOLS, WEB_TOOLS

llm = NvidiaProvider(api_key=os.environ["NVIDIA_API_KEY"])
orch = Orchestrator(llm)
orch.register_tools(FILE_TOOLS + WEB_TOOLS)

result = orch.run("Search for AI news and save to ai_news.txt")
print(result["final_answer"])
```

---

## Core Architecture

```
User Task
    │
    ▼
Orchestrator._plan()          ← LLM plans: single-agent or multi-agent?
    │
    ├─ Single-agent (simple task)
    │   └─ Agent.run() → tool_loop → final answer
    │
    └─ Multi-agent (complex task)
        ├─ Level 0: Agent A ───┐
        ├─ Level 1: Agent B ───┤ (parallel, dependency-aware)
        ├─ Level 2: Agent C ───┘
        └─ Orchestrator._aggregate() → merged final answer
```

The **Orchestrator** is the central controller. It:
1. **Plans** the task using an LLM — decides if sub-agents are needed
2. **Spawns** agents on demand, each with the right tools and skills
3. **Executes** agents in dependency-respecting parallel levels
4. **Aggregates** all agent results into one final answer

---

## LLM Providers

### Built-in: NvidiaProvider

Uses NVIDIA NIM (OpenAI-compatible endpoint):

```python
from mini_agent import NvidiaProvider

# Uses NVIDIA_API_KEY from environment
llm = NvidiaProvider()

# Or explicit configuration
llm = NvidiaProvider(
    api_key="nvapi-...",
    model="deepseek-ai/deepseek-v4-flash",
    temperature=0.7,
    top_p=0.95,
    max_tokens=4096,
)
```

Default model: `mistralai/mistral-medium-3.5-128b`.  
API key must start with `nvapi-`. Get one at [build.nvidia.com](https://build.nvidia.com).

### Custom Provider

Implement `BaseLLMProvider` for any LLM (OpenAI, Anthropic, Ollama, Groq, etc.):

```python
from mini_agent import BaseLLMProvider

class MyProvider(BaseLLMProvider):
    def generate_stream(self, system_prompt: str, user_message: str):
        # Must be a generator yielding tokens one by one
        for token in my_api_call(system_prompt, user_message):
            yield token
```

`generate()` is implemented automatically by accumulating tokens from `generate_stream()`.

---

## Tools

### Tool Class

Every tool is a `Tool` dataclass wrapping a Python function:

```python
from mini_agent import Tool

def get_weather(city: str) -> str:
    return f"{city}: 32°C sunny"

tool = Tool(
    name="get_weather",
    description="Get current weather for a city",
    func=get_weather,
    parameters={"city": "str"},    # auto-detected if omitted
    requires_approval=False,        # gates execution behind approval callback
    read_only=True,                 # available during planning phase
    validator=None,                 # input validation function
    on_error=None,                  # error handler (returns fallback string)
)
```

### Built-in Tool Categories

```python
from mini_agent.registry.builtin import (
    BUILTIN_TOOLS,   # FILE + WEB + DATA + MATH + SYSTEM + BASH
    FILE_TOOLS,      # read_file, write_file, list_dir, ...
    WEB_TOOLS,       # web_search, web_fetch, ...
    DATA_TOOLS,      # csv_to_json, ...
    MATH_TOOLS,      # calculate, ...
    SYSTEM_TOOLS,    # get_env, ...
    BASH_TOOL,       # run_bash
    BROWSER_TOOLS,   # Playwright browser automation (opt-in)
    ALL_TOOLS,       # BUILTIN_TOOLS + BROWSER_TOOLS
)
```

### Tool Approval

Tools with `requires_approval=True` will prompt the user before execution:

```python
from mini_agent import Orchestrator
from mini_agent.core.utils import cli_approval_callback

orch = Orchestrator(llm, approval_callback=cli_approval_callback)
```

**Built-in callbacks:**

| Callback | Behavior |
|----------|----------|
| `cli_approval_callback` | Terminal prompt `[y/N]` |
| `auto_approve_callback` | Always approves (logging mode) |
| `auto_reject_callback` | Always rejects (dry-run / read-only) |

Custom callbacks follow the signature `(tool_name: str, arguments: dict) -> bool`.

### Registering Tools

```python
# Single
orch.register_tool(tool)

# Multiple
orch.register_tools([tool1, tool2])

# Built-in categories
orch.register_tools(FILE_TOOLS + WEB_TOOLS + MATH_TOOLS)
```

---

## Skills

Skills provide domain expertise as Markdown files. They are matched against the task and injected into agent prompts.

### Bundled Skills

Skills are pre-defined `Skill` objects you can import and register just like tools:

```python
from mini_agent.skills.builtin import SKILLS, CODE_REVIEW, DEVELOPER

# Register all bundled skills
orch.register_skills(SKILLS)

# Or select individual skills
orch.register_skills(CODE_REVIEW + DEVELOPER)
```

### Custom Skills

Skills provide domain expertise as Markdown files. They are matched against the task and injected into agent prompts:

```
---
name: code-review
description: Review Python code for bugs, style issues, and security vulnerabilities
---

Your detailed expertise and instructions go here...
```

```python
from mini_agent import Skill

# Single skill
orch.register_skill(Skill(
    name="code-review",
    description="Review Python code for bugs, style, security",
))

# Load from a directory of .md skill files
orch.load_skills_from_dir("path/to/skills/")

# Multiple
orch.register_skills([skill1, skill2])
```

Skills are auto-matched using keyword overlap between the task text and skill descriptions.

---

## Session Management

Manage multi-turn conversations with persistent storage:

```python
from mini_agent import Orchestrator, SessionManager, NvidiaProvider

sm = SessionManager()
orch = Orchestrator(llm, session_manager=sm)

# Create a session
s1 = sm.create_session("AI Discussion")

# Multi-turn chat (streaming, context-aware)
orch.chat("What is machine learning?", session_id=s1["id"])
orch.chat("Explain neural networks", session_id=s1["id"])

# List all sessions
print(sm.list_sessions())
```

### Session API

| Method | Description |
|--------|-------------|
| `create_session(name)` | Create new session |
| `list_sessions()` | List all sessions with metadata |
| `get_session(id)` | Get session memory |
| `delete_session(id)` | Delete a session |
| `rename_session(id, name)` | Rename a session |

### Chat vs Run

| Method | Use Case | Streaming | Agents |
|--------|----------|-----------|--------|
| `chat()` | Conversational Q&A | Yes (live tokens) | No (pure LLM) |
| `run()` | Complex task execution | No | Yes (multi-agent) |

---

## Action Tracking

Real-time event monitoring for debugging and observability:

```python
from mini_agent import Orchestrator, ActionTracker, console_event_logger

tracker = ActionTracker(on_event=console_event_logger)
orch = Orchestrator(llm, action_tracker=tracker)
```

The default `console_event_logger` prints formatted events to stderr:

```
╔═══ PLAN ═══════════════════════════
║  Decision : multi-agent (3 sub-tasks)
║  Task #0 : researcher  [web_search]
║  Task #1 : summarizer  [write_file]
╚════════════════════════════════════

    ┌══ WORKER: researcher ═══════════┐
    │  Search for Python AI frameworks
    │  Tools: web_search, web_fetch
    │  Skills: code-review
    └══════════════════════════════════┘
```

### Events

| Event | Triggered when |
|-------|----------------|
| `plan` | Orchestrator creates a task plan |
| `agent_start` | A worker agent is spawned |
| `agent_end` | A worker agent completes |
| `tool_call` | An agent calls a tool |
| `tool_result` | A tool returns its result |
| `aggregate` | Orchestrator merges agent results |
| `token` | A streaming token is produced |
| `research` | A research action occurs |

Custom event handler:

```python
def my_handler(event_type: str, data: dict):
    print(f"[{event_type}] {data}")

tracker = ActionTracker(on_event=my_handler)
```

---

## Examples

### Multi-Agent Task

```python
result = orch.run(
    "Search for top 3 Python web frameworks, "
    "compare their features, and save the comparison to comparison.md"
)
print(result["final_answer"])
```

### Single Direct Task

Simple tasks bypass the multi-agent system:

```python
result = orch.run("What is 2+2?")
print(result["final_answer"])  # "4"
```

### Interactive CLI

```python
from mini_agent import (
    Orchestrator, NvidiaProvider, SessionManager, Tool, Skill,
    ActionTracker, console_event_logger
)
from mini_agent.registry.builtin import FILE_TOOLS, WEB_TOOLS, MATH_TOOLS
from mini_agent.skills.builtin import CODE_REVIEW

llm = NvidiaProvider(api_key=os.environ["NVIDIA_API_KEY"])
sm = SessionManager()
tracker = ActionTracker(on_event=console_event_logger)
orch = Orchestrator(llm, session_manager=sm, action_tracker=tracker)
orch.register_tools(FILE_TOOLS + WEB_TOOLS + MATH_TOOLS)
orch.register_skills(CODE_REVIEW)

session = sm.create_session("Interactive")

while True:
    user_input = input("\n> ").strip()
    if user_input.lower() in ("exit", "quit"):
        break
    if user_input.startswith("!"):
        result = orch.run(user_input[1:], session_id=session["id"])
        print(f"\n{result['final_answer']}")
    else:
        orch.chat(user_input, session_id=session["id"])
```

---

## Browser Tools (Opt-in)

Requires Playwright:

```bash
pip install mini-agent-framework[browser]
playwright install chromium
```

```python
from mini_agent.registry.builtin import init_browser, BROWSER_TOOLS

# headless=True  → invisible (default)
# headless=False → visible GUI window
init_browser(headless=False)
orch.register_tools(BROWSER_TOOLS)
```

Available: `browser_open`, `browser_click`, `browser_fill`, `browser_select`, `browser_scroll`, `browser_extract`, `browser_screenshot`, `browser_read`, `browser_observe`, `browser_navigate`, `browser_tabs`, `browser_download`, `browser_dialog`, `browser_wait`, `browser_check`, `browser_close`, `browser_javascript`, `browser_upload`.

To toggle between modes at runtime:

```python
init_browser(headless=False)  # switch to visible mode
init_browser(headless=True)   # switch back to headless
```

---

## Configuration

Settings in `mini_agent.config.settings`:

| Setting | Default | Description |
|---------|---------|-------------|
| `MAX_AGENTS` | 5 | Maximum parallel sub-agents per task |
| `MAX_RECURSION_DEPTH` | 2 | Maximum nested agent spawn depth |
| `MAX_TOOL_ITERATIONS` | 5 | Maximum tool calls per agent loop |
| `MEMORY_MAX_TURNS` | 5 | Conversation turns retained (non-session) |
| `SESSION_MAX_TURNS` | 0 | Turns stored per session (0 = unlimited) |
| `MEMORY_CONTEXT_TURNS` | 2 | Recent turns included in agent prompt |

```python
from mini_agent.config.settings import MAX_AGENTS
MAX_AGENTS = 10  # override before creating Orchestrator
```

---

## Dependencies

| Package | Version |
|---------|---------|
| openai | >=1.0 |
| requests | >=2.31 |
| pydantic | >=2.8 |
| python-dotenv | >=1.0 |
| aiohttp | >=3.9 |
| fastapi | >=0.111 |
| uvicorn | >=0.24 |

Optional: `playwright>=1.38` (browser tools)

---

## Development

```bash
# Clone
git clone https://github.com/ayyandurai111/mini-agent-framework.git
cd mini-agent-framework

# Install in editable mode
pip install -e .

# With browser support
pip install -e .[browser]
```

---

## License

MIT License — see [LICENSE](LICENSE).

---

## Links

- **PyPI**: [mini-agent-framework](https://pypi.org/project/mini-agent-framework/)
- **Repository**: [github.com/ayyandurai111/mini-agent-framework](https://github.com/ayyandurai111/mini-agent-framework)
- **Issues**: [github.com/ayyandurai111/mini-agent-framework/issues](https://github.com/ayyandurai111/mini-agent-framework/issues)
