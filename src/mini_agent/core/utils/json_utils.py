"""
core/json_utils.py
---------------------
Shared JSON parsing helper. LLMs sometimes wrap JSON in markdown code
fences despite instructions not to \u2014 this strips that before parsing.
"""

import json
import re
from typing import Optional, Union

_CODE_FENCE_RE = re.compile(r"^```(?:json)?\s*\n?(.*?)\n?```\s*$", re.DOTALL)


def strip_code_fences(text: str) -> str:
    cleaned = text.strip()
    m = _CODE_FENCE_RE.match(cleaned)
    if m:
        return m.group(1).strip()
    return cleaned


def try_parse_json(text: str) -> Optional[Union[dict, list]]:
    """Returns the parsed JSON value, or None if the text isn't valid JSON."""
    if not isinstance(text, str):
        return None
    try:
        return json.loads(strip_code_fences(text))
    except (json.JSONDecodeError, TypeError):
        return None
