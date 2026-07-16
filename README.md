# mini_agent

A dynamic multi-agent AI framework — no fixed agent pool. The Orchestrator plans the task, spawns workers with matched tools and skills at runtime, and aggregates results.

**LLM Provider:** NVIDIA NIM (OpenAI-compatible endpoint).

## Quick Start

```bash
set NVIDIA_API_KEY=nvapi-...
pip install openai requests
```

```python
import os
from mini_agent import Orchestrator
from mini_agent.providers.nvidia_provider import NvidiaProvider

llm = NvidiaProvider(api_key=os.environ["NVIDIA_API_KEY"])
o = Orchestrator(llm)

# Register only the tools you need
from mini_agent.registry.builtin import FILE_TOOLS, WEB_TOOLS
o.register_tools(FILE_TOOLS + WEB_TOOLS)

result = o.run("Search for AI news and save to ai_news.txt")
print(result["final_answer"])
```

## How It Works

```
Task → Orchestrator.run()
         │
         ├─ Planner (read-only ReAct loop) → Plan JSON
         │    ├─ final_answer → return directly (simple questions)
         │    └─ needs_sub_agents → spawn agents
         ├─ Spawn agents with matched tools + skills
         └─ Aggregate results → final answer
```

**Planner:** Two modes — Direct Answer for simple questions (no agents spawned), or Plan for complex tasks needing write/execute tools. Uses read-only tools for research before planning.

**Workers:** Each agent runs a real tool-execution loop. Tool calls actually execute — no LLM hallucinates a file creation without calling `write_text_file`.

**Memory:** Last 2 conversation turns injected into the main agent for continuity. Sub-agents start fresh unless `memory: true` is set in the plan.

## Key Features

- **Two-mode planner** — Direct answer or multi-agent plan
- **Need-based spawning** — Only matched tools per agent, not all tools
- **Explicit registration** — Nothing auto-discovered. You register only what you need
- **Dependency chains** — `depends_on` + `memory: true` for sequential agent pipelines
- **39 built-in tools** across 7 categories
- **2 built-in skills** (code-review, developer) — opt-in via `register_skill()`
- **Custom tools** — Wrap any Python function as a Tool
- **Custom skills** — Markdown workflow files
- **Action tracking** — Real-time structured logging with box-drawing UI
- **Approval workflow** — Gate dangerous tools (bash, delete, download)

## Structure

```
mini_agent/
├── core/
│   ├── orchestrator.py    — plan, spawn, aggregate
│   ├── agent.py           — worker (runs tool loop with system prompt)
│   ├── tool_loop.py       — ReAct loop with tool_history tracking
│   ├── memory/
│   │   └── conversation.py — raw-text turn memory (no LLM summarization)
│   └── utils/
│       ├── action_tracker.py — structured logging (box-drawing output)
│       ├── approval.py       — cli/auto-approve/auto-reject callbacks
│       └── json_utils.py     — JSON parsing helpers
├── llm/
│   └── base.py            — BaseLLMProvider contract
├── prompts/
│   ├── orchestrator_prompt.py — planner system prompt (two-mode)
│   └── prompt_builder.py      — per-agent prompt builder
├── providers/
│   └── nvidia_provider.py — NVIDIA NIM adapter (default: mistralai/mistral-medium-3.5-128b)
├── registry/
│   ├── tools.py           — Tool class + ToolRegistry
│   ├── builtin/           — 39 ready-made tools
│   └── browser/           — 20 granular Playwright automation tools
└── skills/
    ├── __init__.py        — Skill class + registry + discovery
    ├── code-review/       — Code review workflow
    └── developer/         — Code writing workflow
```

## Built-in Tools (39)

Import and register only the categories you need:

| Category | Tools | Import |
|---|---|---|
| **File (6)** | read_text_file, write_text_file, append_text_file, list_directory, file_exists, delete_file | `FILE_TOOLS` |
| **Web (4)** | web_search, fetch_url, scrape_webpage, download_file | `WEB_TOOLS` |
| **Browser (17)** | navigate, click, fill, extract, screenshot, scroll, select, upload, tabs, storage, observe, wait, read, check, dialog, javascript, close | `BROWSER_TOOLS` |
| **Math (4)** | calculator, generate_uuid, random_number, word_count | `MATH_TOOLS` |
| **Data (2)** | read_json, file_exists | `DATA_TOOLS` |
| **System (3)** | get_current_datetime, get_current_working_directory, list_directory | `SYSTEM_TOOLS` |
| **Shell (1)** | bash | `BASH_TOOL` |

### Browser Tools (opt-in, needs Playwright)

```bash
pip install playwright
playwright install chromium
```

```python
from mini_agent.registry.builtin import BROWSER_TOOLS
o.register_tools(BROWSER_TOOLS)
```

17 granular tools: navigate, click, fill_text, extract_text, screenshot, scroll, select_option, file_upload, manage_tabs, manage_storage, observe_page, wait_for, read_page, check_element, handle_dialog, execute_js, close.

## Custom Tools

```python
from mini_agent import Tool

def get_weather(city: str) -> str:
    return f"{city}: 32C sunny"

tool = Tool(name="get_weather", description="Weather info", func=get_weather)
orchestrator.register_tool(tool)
```

Tool parameters auto-detected from function signatures. Override with explicit `parameters=` for dynamic functions. Optional hooks: `validator`, `on_error`, `requires_approval`.

## Skills

Skills are opt-in — register only if needed:

```python
from mini_agent.skills import Skill

# Register a built-in skill
from mini_agent.skills import discover_package_skills
for skill in discover_package_skills():
    o.register_skill(skill)

# Or register a custom skill
o.register_skill(Skill(
    name="my-workflow",
    description="Standard operating procedure for X",
    file_path="./skills/my-workflow/my-workflow.md"
))
```

## Approval Workflow

```python
from mini_agent.core.utils import cli_approval_callback
o = Orchestrator(llm, approval_callback=cli_approval_callback)
```

Terminal prompts before write/delete/bash/download actions.

## Logging (ActionTracker)

Structured box-drawing output shows plan decisions, agent tool assignments, progress, and results:

```
╔═══ PLAN ═══════════════════════════════
║  Decision : single-agent
║  Tools : write_text_file, web_search
║  Skills: developer
╚══════════════════════════════════════

    ┌── WORKER: direct_agent ──────────────┐
    │  Task: Search + write file            │
    │  1/5  ⚙ web_search(query=AI news)    │
    │        → Top story: ...               │
    │  2/5  ⚙ write_text_file(path=...)    │
    │        → Wrote 512 characters         │
    │  ✅ Task complete                     │
    └──────────────────────────────────────┘
```

## Configuration

| Setting | File | Default | Description |
|---|---|---|---|
| MAX_AGENTS | config/settings.py | 5 | Max sub-agents per task |
| MAX_TOOL_ITERATIONS | config/settings.py | 5 | Max tool calls per agent |
| MAX_RECURSION_DEPTH | config/settings.py | 2 | Max recursive spawning depth |
| MEMORY_CONTEXT_TURNS | config/settings.py | 2 | Recent turns injected into main agent |
| Default model | providers/nvidia_provider.py | mistralai/mistral-medium-3.5-128b | Override at construction |

## Demo

```bash
set NVIDIA_API_KEY=nvapi-...
python app.py
```

Interactive chatbot with all 39 tools, 2 opt-in skills, and session memory.

## Author

ayyandurai (ayyandurai456@gmail.com)

## License

MIT
