# mini-agent-framework

A dynamic multi-agent AI framework — no fixed agent pool. The Orchestrator plans the task, spawns workers with matched tools and skills at runtime, and aggregates results.

```bash
pip install mini-agent-framework
```

## Basic Usage

```python
import os
from mini_agent import Orchestrator, NvidiaProvider
from mini_agent.registry.builtin import FILE_TOOLS, WEB_TOOLS

llm = NvidiaProvider(api_key=os.environ["NVIDIA_API_KEY"])
o = Orchestrator(llm)
o.register_tools(FILE_TOOLS + WEB_TOOLS)

result = o.run("Search for AI news and save to ai_news.txt")
print(result["final_answer"])
```

## Sessions (multi-turn chat)

```python
from mini_agent import Orchestrator, SessionManager, NvidiaProvider

sm = SessionManager()
orch = Orchestrator(llm_provider=provider, session_manager=sm)

s1 = sm.create_session("my chat")
sm.list_sessions()

reply = orch.chat("hello", session_id=s1["id"])   # remembers context
reply = orch.chat("what is AI?", session_id=s1["id"])
```

## Streaming

```python
for event in orch.chat_stream("tell me a story", session_id=s1["id"]):
    if event["type"] == "token":
        print(event["content"], end="", flush=True)
```

## Browser Tools (opt-in)

```bash
pip install mini-agent-framework[browser]
playwright install chromium
```

```python
from mini_agent.registry.builtin import BROWSER_TOOLS
o.register_tools(BROWSER_TOOLS)
```

## Custom Tools

```python
from mini_agent import Tool

def get_weather(city: str) -> str:
    return f"{city}: 32C sunny"

o.register_tool(Tool(name="get_weather", description="Weather info", func=get_weather))
```

## License

MIT
