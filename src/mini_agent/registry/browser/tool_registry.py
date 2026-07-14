from __future__ import annotations

from typing import Any, Dict, List

from .engine import BrowserManager
from .exceptions import UnknownToolError
from .logger import get_logger
from .models import ToolResponse
from .tools.base import BaseTool
from .tools.check import CheckTool
from .tools.click import ClickTool
from .tools.close import CloseTool
from .tools.dialog import DialogTool
from .tools.download import DownloadTool
from .tools.extract import ExtractTool
from .tools.fill import FillTool
from .tools.javascript import ExecuteJSTool
from .tools.navigate import NavigateTool
from .tools.observe import ObserveTool
from .tools.open import OpenTool
from .tools.read import ReadTool
from .tools.screenshot import ScreenshotTool
from .tools.scroll import ScrollTool
from .tools.select import SelectTool
from .tools.storage import StorageTool
from .tools.tabs import TabsTool
from .tools.upload import UploadTool
from .tools.wait import WaitTool

logger = get_logger(__name__)

_TOOL_CLASSES: List[type] = [
    OpenTool,
    ObserveTool,
    ClickTool,
    FillTool,
    SelectTool,
    CheckTool,
    ScrollTool,
    WaitTool,
    NavigateTool,
    TabsTool,
    UploadTool,
    DownloadTool,
    DialogTool,
    ReadTool,
    ExtractTool,
    ExecuteJSTool,
    StorageTool,
    ScreenshotTool,
    CloseTool,
]


class ToolRegistry:
    def __init__(self, browser_manager: BrowserManager):
        self._browser = browser_manager
        self._tools: Dict[str, BaseTool] = {
            cls.name: cls(browser_manager) for cls in _TOOL_CLASSES
        }
        logger.debug("Registered tools: %s", sorted(self._tools))

    def register(self, tool_cls: type) -> None:
        instance = tool_cls(self._browser)
        self._tools[instance.name] = instance
        logger.info("Registered additional tool '%s'", instance.name)

    def list_tools(self) -> List[str]:
        return sorted(self._tools)

    async def dispatch(self, tool_name: str, **params: Any) -> ToolResponse:
        tool = self._tools.get(tool_name)
        if tool is None:
            raise UnknownToolError(
                f"Unknown tool '{tool_name}'. Available tools: {', '.join(self.list_tools())}",
                requested=tool_name,
            )
        return await tool.execute(**params)
