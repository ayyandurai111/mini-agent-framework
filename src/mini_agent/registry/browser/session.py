from __future__ import annotations

from typing import Any, Dict, List, Optional

from .engine import BrowserManager
from .exceptions import BrowserAgentError
from .logger import get_logger
from .models import ToolResponse
from .tool_registry import ToolRegistry

logger = get_logger(__name__)


class BrowserSession:
    def __init__(
        self,
        headless: bool = True,
        downloads_dir: str = "./downloads",
        screenshots_dir: str = "./screenshots",
        viewport: Optional[Dict[str, int]] = None,
        user_agent: Optional[str] = None,
        default_timeout_ms: int = 30_000,
        proxy: Optional[Dict[str, str]] = None,
        version_main: Optional[int] = None,
    ):
        self._manager = BrowserManager(
            headless=headless,
            downloads_dir=downloads_dir,
            screenshots_dir=screenshots_dir,
            viewport=viewport,
            user_agent=user_agent,
            default_timeout_ms=default_timeout_ms,
            proxy=proxy,
            version_main=version_main,
        )
        self._registry = ToolRegistry(self._manager)
        self._started = False

    def start(self) -> None:
        self._manager.start()
        self._started = True

    def shutdown(self) -> None:
        self._manager.shutdown()
        self._started = False

    def __enter__(self) -> "BrowserSession":
        self.start()
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.shutdown()

    def call(self, tool_name: str, **params: Any) -> Dict[str, Any]:
        if not self._started:
            return ToolResponse.fail(
                tool=tool_name,
                message="Browser not started",
                error="Call agent.start() before invoking tools.",
                error_code="browser_not_started",
            ).to_dict()

        try:
            response = self._registry.dispatch(tool_name, **params)
        except BrowserAgentError as exc:
            response = ToolResponse.fail(
                tool=tool_name, message="Tool dispatch failed", error=exc.message, error_code=exc.code
            )
        except TypeError as exc:
            response = ToolResponse.fail(
                tool=tool_name,
                message="Invalid parameters for tool",
                error=str(exc),
                error_code="invalid_params",
            )
        return response.to_dict()

    def list_tools(self) -> List[str]:
        return self._registry.list_tools()

    def register_tool(self, tool_cls: type) -> None:
        self._registry.register(tool_cls)

    def open(self, url: str, **kwargs) -> Dict[str, Any]:
        return self.call("open", url=url, **kwargs)

    def observe(self, **kwargs) -> Dict[str, Any]:
        return self.call("observe", **kwargs)

    def click(self, **kwargs) -> Dict[str, Any]:
        return self.call("click", **kwargs)

    def fill(self, value: str, **kwargs) -> Dict[str, Any]:
        return self.call("fill", value=value, **kwargs)

    def select(self, **kwargs) -> Dict[str, Any]:
        return self.call("select", **kwargs)

    def check(self, checked: bool = True, **kwargs) -> Dict[str, Any]:
        return self.call("check", checked=checked, **kwargs)

    def scroll(self, **kwargs) -> Dict[str, Any]:
        return self.call("scroll", **kwargs)

    def wait(self, **kwargs) -> Dict[str, Any]:
        return self.call("wait", **kwargs)

    def navigate(self, action: str, **kwargs) -> Dict[str, Any]:
        return self.call("navigate", action=action, **kwargs)

    def tabs(self, action: str, **kwargs) -> Dict[str, Any]:
        return self.call("tabs", action=action, **kwargs)

    def upload(self, file_paths, **kwargs) -> Dict[str, Any]:
        return self.call("upload", file_paths=file_paths, **kwargs)

    def download(self, **kwargs) -> Dict[str, Any]:
        return self.call("download", **kwargs)

    def dialog(self, **kwargs) -> Dict[str, Any]:
        return self.call("dialog", **kwargs)

    def read(self, **kwargs) -> Dict[str, Any]:
        return self.call("read", **kwargs)

    def extract(self, kind: str = "tables", **kwargs) -> Dict[str, Any]:
        return self.call("extract", kind=kind, **kwargs)

    def execute_js(self, code: str, **kwargs) -> Dict[str, Any]:
        return self.call("execute_js", code=code, **kwargs)

    def storage(self, **kwargs) -> Dict[str, Any]:
        return self.call("storage", **kwargs)

    def screenshot(self, **kwargs) -> Dict[str, Any]:
        return self.call("screenshot", **kwargs)

    def close(self, scope: str = "tab", **kwargs) -> Dict[str, Any]:
        return self.call("close", scope=scope, **kwargs)
