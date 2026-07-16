"""
core/approval.py
-------------------
Ready-made approval callbacks. An approval_callback is any function with
signature (tool_name: str, arguments: dict) -> bool. Pass one to
Orchestrator(approval_callback=...) to have the tool loop pause and ask
before running any Tool with requires_approval=True â€” same idea as
Claude Code confirming before file edits or bash commands.

If no approval_callback is given, tools run automatically regardless of
requires_approval (fully backward compatible / fully autonomous mode).
"""


def cli_approval_callback(tool_name: str, arguments: dict) -> bool:
    """Prompts on the terminal and blocks until the user answers y/n."""
    prompt = f"\nApprove running '{tool_name}' with arguments {arguments}? [y/N]: "
    try:
        answer = input(prompt).strip().lower()
        return answer in ("y", "yes")
    except (EOFError, OSError):
        return False


def auto_approve_callback(tool_name: str, arguments: dict) -> bool:
    """Approves everything automatically â€” useful for logging/audit without
    actually blocking execution (combine with your own logging inside)."""
    return True


def auto_reject_callback(tool_name: str, arguments: dict) -> bool:
    """Rejects every approval-gated tool call â€” useful for a fully
    read-only / dry-run mode."""
    return False
