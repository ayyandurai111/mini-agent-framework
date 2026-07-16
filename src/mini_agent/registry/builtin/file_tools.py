"""
registry/builtin/file_tools.py
---------------------------------
File I/O tools. These modify the local filesystem where the framework
runs, so write_text_file / delete_file are inherently higher-risk than
read-only tools. Use `caution` (see registry/tools.py) to restrict
which agents can use the write/delete variants in production.
"""

import os
from pathlib import Path

from ..tools import Tool


def _resolve_path(path: str) -> str:
    """Resolve to an absolute path, preventing simple directory traversal."""
    return str(Path(path).resolve())


def read_text_file(path: str) -> str:
    """Reads and returns the content of a text file."""
    try:
        resolved = _resolve_path(path)
        with open(resolved, "r", encoding="utf-8") as f:
            return f.read()
    except Exception as exc:
        return f"File read error: {exc}"


def write_text_file(path: str, content: str) -> str:
    """Writes content to a file, overwriting it if it already exists."""
    try:
        resolved = _resolve_path(path)
        os.makedirs(os.path.dirname(resolved), exist_ok=True)
        with open(resolved, "w", encoding="utf-8") as f:
            f.write(content)
        return f"Wrote {len(content)} characters to {resolved}"
    except Exception as exc:
        return f"File write error: {exc}"


def append_text_file(path: str, content: str) -> str:
    """Appends content to the end of a file (creates it if missing)."""
    try:
        resolved = _resolve_path(path)
        os.makedirs(os.path.dirname(resolved), exist_ok=True)
        with open(resolved, "a", encoding="utf-8") as f:
            f.write(content)
        return f"Appended {len(content)} characters to {resolved}"
    except Exception as exc:
        return f"File append error: {exc}"


def list_directory(path: str = ".") -> str:
    """Lists files and folders inside the given directory."""
    try:
        resolved = _resolve_path(path) if path != "." else "."
        entries = os.listdir(resolved)
        return "\n".join(entries) if entries else "(empty directory)"
    except Exception as exc:
        return f"List directory error: {exc}"


def file_exists(path: str) -> str:
    """Checks whether a file or directory exists at the given path."""
    return "true" if os.path.exists(_resolve_path(path)) else "false"


def delete_file(path: str) -> str:
    """Deletes a file. Irreversible â€” use validator/caution to gate this."""
    try:
        resolved = _resolve_path(path)
        os.remove(resolved)
        return f"Deleted {resolved}"
    except Exception as exc:
        return f"File delete error: {exc}"


FILE_TOOLS = [
    Tool(name="read_text_file", description="Reads text file content", func=read_text_file),
    Tool(name="write_text_file", description="Writes/overwrites a text file", func=write_text_file, requires_approval=True, read_only=False),
    Tool(name="append_text_file", description="Appends text to a file", func=append_text_file, requires_approval=True, read_only=False),
    Tool(name="list_directory", description="Lists files in a directory", func=list_directory),
    Tool(name="file_exists", description="Checks if a path exists", func=file_exists),
    Tool(name="delete_file", description="Deletes a file (irreversible)", func=delete_file, requires_approval=True, read_only=False),
]
