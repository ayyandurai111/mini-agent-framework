"""
registry/builtin/bash_tool.py
--------------------------------
Unified shell tool â€” replaces run_command, execute_python_code,
install_package, and list_processes with one tool.
"""

import subprocess

from ..tools import Tool


def bash(command: str, timeout: int = 30) -> str:
    """
    Executes any shell command (bash, python, pip, etc.) and returns output.
    Full OS access â€” restrict with allowed_roles in production.
    """
    if not command or not command.strip():
        return "Error: no command provided"
    try:
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        output = result.stdout
        if result.stderr:
            output += f"\n[stderr]\n{result.stderr}"
        output = output[:4000] + ("... (truncated)" if len(output) > 4000 else "")
        return output if output.strip() else "(no output)"
    except subprocess.TimeoutExpired:
        return f"Error: command exceeded {timeout}s timeout"
    except Exception as exc:
        return f"Command error: {exc}"


BASH_TOOL = [
    Tool(
        name="bash",
        description="Executes any shell command (bash, python, pip, etc.) â€” full OS access",
        func=bash,
        requires_approval=True,
        read_only=False,
    ),
]
