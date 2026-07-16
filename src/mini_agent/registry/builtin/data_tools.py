"""
registry/builtin/data_tools.py
---------------------------------
Structured data (JSON) read/write helpers.
"""

import json

from ..tools import Tool


def read_json(path: str) -> str:
    """Reads a JSON file and returns it as a formatted string."""
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return json.dumps(data, indent=2)
    except Exception as exc:
        return f"JSON read error: {exc}"


DATA_TOOLS = [
    Tool(name="read_json", description="Reads and pretty-prints a JSON file", func=read_json),
]
