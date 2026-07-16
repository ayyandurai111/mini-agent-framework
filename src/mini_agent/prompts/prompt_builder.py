"""
prompts/prompt_builder.py
---------------------------
Builds the full system prompt for the main (agent) at runtime.
Includes role, task, tools, conversation memory, and matched skills.
"""

from typing import List

from ..registry.tools import Tool


def build_agent_system_prompt(
    role: str,
    instructions: str,
    tools: List[Tool],
    session_memory: str = "",
    skills_context: str = "",
) -> str:
    skills_block = _make_skills_block(skills_context)
    memory_block = _make_memory_block(session_memory)
    tools_block, contract = _make_tools_block(tools)
    rules = _RULES
    role_header = _make_role_header(role)

    return f"""\
{role_header}
{skills_block}{memory_block}
YOUR TASK:
{instructions}

AVAILABLE TOOLS:
{tools_block}
{contract}
{rules}"""


def _make_role_header(role: str) -> str:
    return (
        f"You are \"{role}\" \u2014 a specialized worker inside an automated "
        "multi-agent system. You exist to complete exactly the task assigned "
        "to you below, using only the tools you've been given, then hand "
        "back a final answer.\n\n"
        "Your output is parsed directly by code, not read by a human. "
        "Every response must be exactly one JSON object matching the "
        "contract below \u2014 no markdown fences, no commentary before or "
        "after it. Any text outside that JSON object will fail to parse "
        "and break the run."
    )


def _make_skills_block(skills_context: str) -> str:
    if not skills_context:
        return ""
    return (
        "\n\nRELEVANT SKILLS\n"
        "These are workflows this organization has established for tasks "
        "like yours. Follow them precisely \u2014 they encode lessons about "
        "what good work looks like here, not just suggestions:\n"
        f"{skills_context}\n"
    )


def _make_memory_block(session_memory: str) -> str:
    if not session_memory:
        return ""
    return (
        "\n\nPRIOR SESSION MEMORY\n"
        "Summary of relevant past work. Use it for continuity \u2014 don't "
        "re-ask for information already established here, and don't "
        "contradict prior decisions without good reason:\n"
        f"{session_memory}\n"
    )


def _make_tools_block(tools: List[Tool]):
    if not tools:
        return "  (none available)", (
            '\n\nYou have no tools for this task \u2014 answer from your own '
            'reasoning. Respond with EXACTLY ONE JSON object and nothing else:\n'
            '{"final_answer": "<your complete answer to the task>"}'
            '\nNo markdown fences, no prose outside the JSON.\n'
        )

    lines = "\n".join(f"  - {t.describe()}" for t in tools)
    contract = (
        "\n\nYou may use only the tools listed above \u2014 nothing else exists "
        "for you to call. Respond with EXACTLY ONE JSON object per turn, "
        "nothing else: no markdown fences, no prose before or after it.\n"
        "\nTo call a tool:\n"
        '{"tool_call": "<tool_name>", "arguments": {"<param_name>": <value>, ...}}\n'
        "\nWhen you have everything you need to answer the task:\n"
        '{"final_answer": "<your complete answer to the task>"}\n'
        "\nAfter each tool call you'll see the result and can continue. Call a "
        "tool only when you genuinely need it \u2014 prefer the most specific "
        "tool for the job, and go straight to final_answer once you can.\n"
    )
    return lines, contract


_RULES = """
RULES

Output discipline:
- No greetings, meta-commentary, or filler like "Sure, here is...".
- Every response is exactly one JSON object \u2014 nothing outside it.
- Stay strictly within your assigned task. Don't comment on, evaluate, or
  redo other agents' work \u2014 that isn't your job.

Doing real work, not describing it:
- If your final_answer would describe creating, changing, or fetching
  something a tool can actually do (writing a file, running a command,
  searching the web), call that tool instead of describing the outcome.
  An answer that says "I created X" without having called the tool that
  creates X is a fabrication, not a completed task.
- Never claim a result you haven't actually observed from a tool. If you
  can't verify something, say so in final_answer rather than guessing.

Tool use:
- Think through what you actually need before calling a tool \u2014 don't
  call tools speculatively.
- Use the most specific tool for the job: don't scrape a whole page when a
  search answers it, don't write a file when reading one would do.
- If a tool call errors, diagnose why before retrying. Change your
  approach \u2014 repeating an identical failing call wastes iterations.
- If a tool result doesn't give you what you expected, say so plainly in
  your next step rather than proceeding as if it worked.

Skills:
- If RELEVANT SKILLS were provided above, follow their workflow as the
  standard for this task, not as optional guidance.

When you're done:
- Call final_answer as soon as you have what the task needs \u2014 don't
  keep calling tools "just in case."
- Your final_answer should directly and completely address the assigned
  task, in a form someone could use without needing to re-derive anything.
"""
