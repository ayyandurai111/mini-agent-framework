# mini_agent

A dynamic multi-agent AI framework — no fixed agent pool. The Orchestrator plans the task, spawns workers with matched tools and skills at runtime, and aggregates results.

**LLM Provider:** NVIDIA NIM (OpenAI-compatible endpoint).

## Quick Start

```bash
export NVIDIA_API_KEY=nvapi-...
pip install openai requests
```

```python
import os
from mini_agent import Orchestrator
from mini_agent.providers.nvidia_provider import NvidiaProvider

llm = NvidiaProvider(api_key=os.environ["NVIDIA_API_KEY"])
o = Orchestrator(llm)

from mini_agent.registry.builtin import BUILTIN_TOOLS
o.register_tools(BUILTIN_TOOLS)

result = o.run("write hello.txt with content Hello World!")
print(result["final_answer"])
```

## How It Works

```
Task → Orchestrator.run()
         │
         ├─ Planner (read-only ReAct loop) → Plan JSON
         ├─ Match skills (code-review, developer, etc.)
         ├─ Spawn agents with matched tools + skills
         └─ Aggregate results → final answer
```

**Planner:** The orchestrator runs a ReAct loop with read-only tools (web_search, read_text_file, etc.) to research before outputting a split plan. It decides whether a single agent or multiple sub-agents are needed.

**Workers:** Each agent runs a real tool-execution loop. Tool calls actually execute — no LLM hallucinates a file creation without calling `write_text_file`.

## Structure

```
mini_agent/
├── core/
│   ├── orchestrator.py    — plan, spawn, aggregate
│   ├── agent.py           — worker (runs tool loop with system prompt)
│   ├── tool_loop.py       — ReAct loop: LLM → tool_call → result → repeat
│   ├── memory/
│   │   └── conversation.py — LLM-compressed session memory
│   └── utils/
│       ├── action_tracker.py — structured logging (box-drawing output)
│       ├── approval.py       — cli/auto-approve/auto-reject callbacks
│       └── json_utils.py     — JSON parsing helpers
├── llm/
│   └── base.py            — BaseLLMProvider (socket/contract)
├── prompts/
│   ├── orchestrator_prompt.py — planner system prompt
│   └── prompt_builder.py      — per-agent prompt builder
├── providers/
│   └── nvidia_provider.py — NVIDIA NIM adapter (default model: deepseek-ai/deepseek-v4-pro)
├── registry/
│   ├── tools.py           — Tool class + ToolRegistry
│   ├── builtin/           — 19 ready-made tools
│   │   ├── file_tools.py, web_tools.py, data_tools.py
│   │   ├── math_tools.py, system_tools.py, bash_tool.py
│   │   └── browser_tools.py (opt-in, needs playwright)
│   └── browser/           — 20 granular browser automation tools
└── skills/
    ├── code-review/
    └── developer/
```

## Built-in Tools (19)

| Category | Tools | In BUILTIN_TOOLS? |
|---|---|---|
| **File** | read_text_file, write_text_file, append_text_file, list_directory, file_exists, delete_file | Yes |
| **Web** | web_search, fetch_url, browse_url, scrape_webpage, download_file | Yes |
| **Data** | read_json | Yes |
| **Math** | calculator, generate_uuid, random_number, word_count | Yes |
| **System** | get_current_datetime, get_current_working_directory | Yes |
| **Shell** | bash | Yes (requires_approval) |

### Opt-in: Browser Tools

```bash
pip install mini_agent[browser]
mini-agent-install-browser
```

Then register `BROWSER_TOOLS` (open_browser, click, type_text, navigate, screenshot, etc. — 20 granular tools).

## Custom Tools

```python
from mini_agent import Tool

def get_weather(city: str) -> str:
    return f"{city}: 32C sunny"

tool = Tool(name="get_weather", description="Weather info", func=get_weather)
orchestrator.register_tool(tool)
```

Tool parameters are auto-detected from function signatures. Override with explicit `parameters=` dict for dynamic functions. Optional hooks: `validator`, `on_error`, `allowed_roles`, `requires_approval`.

## Approval Workflow

```python
from mini_agent.core.utils import cli_approval_callback
o = Orchestrator(llm, approval_callback=cli_approval_callback)
```

Terminal prompts before write/delete/bash/download actions.

## Skills

Skills are markdown files in `skills/<name>/<name>.md` with frontmatter. Matched automatically by keyword overlap with the task.

## Logging (ActionTracker)

Structured box-drawing output shows plan decisions, agent tool assignments, progress, and results:

```
╔═══ PLAN ═══════════════════════════════
║  Decision : single-agent
║  Skills: developer
╚══════════════════════════════════════

    ┌── WORKER: direct_agent ──────────────┐
    │  Task: write hello.txt                │
    │  Tools: write_text_file, bash ...     │
    │  1/5  ⚙ write_text_file(path=...)    │
    │        → Wrote 12 characters          │
    │  ✅ File written                      │
    └──────────────────────────────────────┘
```

## Configuration

| Setting | File | Default | Description |
|---|---|---|---|
| MAX_AGENTS | config/settings.py | 5 | Max sub-agents per task |
| MAX_TOOL_ITERATIONS | config/settings.py | 5 | Max tool calls per agent |
| MAX_RECURSION_DEPTH | config/settings.py | 2 | Max recursive spawning depth |
| Default model | providers/nvidia_provider.py | deepseek-ai/deepseek-v4-pro | Override at construction |

## License

MIT
