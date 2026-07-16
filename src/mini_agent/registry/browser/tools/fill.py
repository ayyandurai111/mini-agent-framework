from ..exceptions import ElementNotFoundError
from ..models import ToolResponse
from .base import BaseTool


class FillTool(BaseTool):
    name = "fill"
    description = "Type text into an input/textarea element"

    async def run(self, value: str, ref: str = None, selector: str = None,
                  text: str = None, role: str = None,
                  clear_first: bool = True, press_enter: bool = False,
                  simulate_typing: bool = False,
                  timeout_ms: int = 10000) -> ToolResponse:
        try:
            locator = await self.resolve_locator(ref=ref, selector=selector,
                                                  text=text, role=role)
            if clear_first:
                await locator.clear()
            if simulate_typing:
                await locator.type(value, delay=20)
            else:
                await locator.fill(value, timeout=timeout_ms)
            if press_enter:
                await locator.press("Enter")
            return ToolResponse.ok(
                tool=self.name,
                message=f"Filled '{value[:50]}' into element",
                data={"value_preview": value[:100]},
            )
        except ElementNotFoundError:
            raise
        except Exception as exc:
            raise ElementNotFoundError(f"Fill failed: {exc}") from exc
