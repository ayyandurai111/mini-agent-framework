from ..exceptions import ElementNotFoundError
from ..models import ToolResponse
from .base import BaseTool


class CheckTool(BaseTool):
    name = "check"
    description = "Check or uncheck a checkbox/radio button"

    async def run(self, checked: bool = True, ref: str = None,
                  selector: str = None, text: str = None,
                  role: str = None, timeout_ms: int = 10000) -> ToolResponse:
        try:
            locator = await self.resolve_locator(ref=ref, selector=selector,
                                                  text=text, role=role)
            if checked:
                await locator.check(timeout=timeout_ms)
            else:
                await locator.uncheck(timeout=timeout_ms)
            state = "checked" if checked else "unchecked"
            return ToolResponse.ok(tool=self.name, message=f"Element {state}")
        except ElementNotFoundError:
            raise
        except Exception as exc:
            raise ElementNotFoundError(f"Check failed: {exc}") from exc
