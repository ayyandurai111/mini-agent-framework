from ..exceptions import BrowserTimeoutError, ElementNotFoundError, InvalidToolParamsError
from ..models import ToolResponse
from .base import BaseTool


class WaitTool(BaseTool):
    name = "wait"
    description = "Wait for load state, element, or timeout"

    async def run(self, for_: str = "load_state", load_state: str = "load",
                  milliseconds: int = 1000, ref: str = None,
                  selector: str = None, timeout_ms: int = 30000) -> ToolResponse:
        try:
            page = self.get_page()
            if for_ == "load_state":
                await page.wait_for_load_state(load_state, timeout=timeout_ms)
                return ToolResponse.ok(tool=self.name, message=f"Load state '{load_state}' reached")
            elif for_ == "selector":
                if not selector:
                    raise InvalidToolParamsError("'selector' param required when for_='selector'")
                await page.wait_for_selector(selector, timeout=timeout_ms)
                return ToolResponse.ok(tool=self.name, message=f"Selector '{selector}' appeared")
            elif for_ == "ref" or for_ == "element":
                locator = await self.resolve_locator(ref=ref, selector=selector, timeout_ms=timeout_ms)
                await locator.wait_for(state="visible", timeout=timeout_ms)
                return ToolResponse.ok(tool=self.name, message="Element visible")
            elif for_ == "timeout":
                import asyncio
                await asyncio.sleep(milliseconds / 1000)
                return ToolResponse.ok(tool=self.name, message=f"Waited {milliseconds}ms")
            elif for_ == "navigation":
                await page.wait_for_url(page.url, timeout=timeout_ms)
                return ToolResponse.ok(tool=self.name, message="Navigation completed")
            else:
                raise InvalidToolParamsError(f"Unknown wait type '{for_}'")
        except (ElementNotFoundError, InvalidToolParamsError, BrowserTimeoutError):
            raise
        except Exception as exc:
            raise BrowserTimeoutError(f"Wait failed: {exc}") from exc
