from ..exceptions import ElementNotFoundError
from ..models import ToolResponse
from .base import BaseTool


class ClickTool(BaseTool):
    name = "click"
    description = "Click an element by ref, CSS selector, or text"

    async def run(self, ref: str = None, selector: str = None,
                  text: str = None, role: str = None,
                  button: str = "left", double_click: bool = False,
                  timeout_ms: int = 10000) -> ToolResponse:
        try:
            locator = await self.resolve_locator(ref=ref, selector=selector,
                                                  text=text, role=role)
            if double_click:
                await locator.dblclick(button=button, timeout=timeout_ms)
            else:
                await locator.click(button=button, timeout=timeout_ms)
            return ToolResponse.ok(
                tool=self.name,
                message=f"Clicked element ({ref or selector or text or role})",
            )
        except ElementNotFoundError:
            raise
        except Exception as exc:
            raise ElementNotFoundError(f"Click failed: {exc}") from exc
