"""
registry/tools.py
-------------------
Tool class — wraps a Python function with metadata for the agent loop.
ToolRegistry maps capability names to tool objects.
"""

import inspect
from dataclasses import dataclass
from typing import Callable, Dict, List, Optional


@dataclass
class Tool:
    name: str
    description: str
    func: Callable
    parameters: Optional[Dict[str, str]] = None
    validator: Optional[Callable[..., bool]] = None
    on_error: Optional[Callable[[Exception], str]] = None
    requires_approval: bool = False
    read_only: bool = True

    def __post_init__(self):
        if not self.name or not self.name.strip():
            raise ValueError("Tool 'name' is required")
        if not self.description:
            raise ValueError(f"Tool '{self.name}' has no description")
        if self.parameters is None:
            self.parameters = self._auto_detect_parameters()

    def _auto_detect_parameters(self) -> Dict[str, str]:
        schema = {}
        try:
            sig = inspect.signature(self.func)
        except (ValueError, TypeError):
            return {"*args": "any (fallback — could not inspect signature)"}
        for param_name, param in sig.parameters.items():
            type_name = (
                param.annotation.__name__
                if param.annotation is not inspect._empty
                else "any"
            )
            required = param.default is inspect._empty
            suffix = "" if required else f" (optional, default={param.default})"
            schema[param_name] = f"{type_name}{suffix}"
        return schema

    def run(self, *args, **kwargs):
        if self.validator is not None:
            ok = self.validator(*args, **kwargs)
            if ok is False:
                raise ValueError(f"Validation failed for tool '{self.name}' with args={args} kwargs={kwargs}")

        try:
            return self.func(*args, **kwargs)
        except Exception as exc:
            if self.on_error is not None:
                return self.on_error(exc)
            raise

    def describe(self) -> str:
        params_str = ", ".join(f"{k}: {v}" for k, v in self.parameters.items()) or "no arguments"
        return f"{self.name}({params_str}) - {self.description}"


class RegistryError(Exception):
    pass


class ToolRegistry:
    def __init__(self):
        self._tools: Dict[str, Tool] = {}

    def register(self, tool: Tool):
        if not tool.name or not tool.name.strip():
            raise RegistryError("Tool name cannot be empty")
        if not tool.description:
            raise RegistryError(f"Tool '{tool.name}' has no description")
        if tool.name in self._tools:
            import warnings
            warnings.warn(f"Tool '{tool.name}' already registered — overwriting")
        self._tools[tool.name] = tool

    def unregister(self, name: str):
        self._tools.pop(name, None)

    def get(self, name: str) -> Tool:
        return self._tools.get(name)

    def match(self, capability_names: List[str]) -> List[Tool]:
        return [self._tools[name] for name in capability_names if name in self._tools]

    def list_available(self) -> List[str]:
        return list(self._tools.keys())

    def get_read_only(self) -> List[str]:
        return [name for name, t in self._tools.items() if t.read_only]
