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
        browser_type: str = "chromium",
        downloads_dir: str = "./downloads",
        screenshots_dir: str = "./screenshots",
        viewport: Optional[Dict[str, int]] = None,
        user_agent: Optional[str] = None,
        default_timeout_ms: int = 30_000,
        slow_mo_ms: int = 0,
        proxy: Optional[Dict[str, str]] = None,
    ):
        self._manager = BrowserManager(
            headless=headless,
            browser_type=browser_type,
            downloads_dir=downloads_dir,
            screenshots_dir=screenshots_dir,
            viewport=viewport,
            user_agent=user_agent,
            default_timeout_ms=default_timeout_ms,
            slow_mo_ms=slow_mo_ms,
            proxy=proxy,
        )
        self._registry = ToolRegistry(self._manager)
        self._started = False

    async def start(self) -> None:
        await self._manager.start()
        self._started = True

    async def shutdown(self) -> None:
        await self._manager.shutdown()
        self._started = False

    async def __aenter__(self) -> "BrowserSession":
        await self.start()
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        await self.shutdown()

    async def call(self, tool_name: str, **params: Any) -> Dict[str, Any]:
        if not self._started:
            return ToolResponse.fail(
                tool=tool_name,
                message="Browser not started",
                error="Call agent.start() before invoking tools.",
                error_code="browser_not_started",
            ).to_dict()

        try:
            response = await self._registry.dispatch(tool_name, **params)
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

    async def open(self, url: str, **kwargs) -> Dict[str, Any]:
        return await self.call("open", url=url, **kwargs)

    async def observe(self, **kwargs) -> Dict[str, Any]:
        return await self.call("observe", **kwargs)

    async def click(self, **kwargs) -> Dict[str, Any]:
        return await self.call("click", **kwargs)

    async def fill(self, value: str, **kwargs) -> Dict[str, Any]:
        return await self.call("fill", value=value, **kwargs)

    async def select(self, **kwargs) -> Dict[str, Any]:
        return await self.call("select", **kwargs)

    async def check(self, checked: bool = True, **kwargs) -> Dict[str, Any]:
        return await self.call("check", checked=checked, **kwargs)

    async def scroll(self, **kwargs) -> Dict[str, Any]:
        return await self.call("scroll", **kwargs)

    async def wait(self, **kwargs) -> Dict[str, Any]:
        return await self.call("wait", **kwargs)

    async def navigate(self, action: str, **kwargs) -> Dict[str, Any]:
        return await self.call("navigate", action=action, **kwargs)

    async def tabs(self, action: str, **kwargs) -> Dict[str, Any]:
        return await self.call("tabs", action=action, **kwargs)

    async def upload(self, file_paths, **kwargs) -> Dict[str, Any]:
        return await self.call("upload", file_paths=file_paths, **kwargs)

    async def download(self, **kwargs) -> Dict[str, Any]:
        return await self.call("download", **kwargs)

    async def dialog(self, **kwargs) -> Dict[str, Any]:
        return await self.call("dialog", **kwargs)

    async def read(self, **kwargs) -> Dict[str, Any]:
        return await self.call("read", **kwargs)

    async def extract(self, kind: str = "tables", **kwargs) -> Dict[str, Any]:
        return await self.call("extract", kind=kind, **kwargs)

    async def execute_js(self, code: str, **kwargs) -> Dict[str, Any]:
        return await self.call("execute_js", code=code, **kwargs)

    async def storage(self, **kwargs) -> Dict[str, Any]:
        return await self.call("storage", **kwargs)

    async def screenshot(self, **kwargs) -> Dict[str, Any]:
        return await self.call("screenshot", **kwargs)

    async def close(self, scope: str = "tab", **kwargs) -> Dict[str, Any]:
        return await self.call("close", scope=scope, **kwargs)
