from ..exceptions import ElementNotFoundError
from ..models import ToolResponse
from .base import BaseTool


class ScrollTool(BaseTool):
    name = "scroll"

    async def run(self, direction: str = "down", amount_px: int = 600,
                  to_bottom: bool = False, to_top: bool = False,
                  ref: str = None, selector: str = None) -> ToolResponse:
        try:
            page = self.get_page()
            if ref or selector:
                locator = await self.resolve_locator(ref=ref, selector=selector)
                await locator.scroll_into_view_if_needed()
                return ToolResponse.ok(tool=self.name, message=f"Scrolled to element")

            if to_bottom:
                await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                return ToolResponse.ok(tool=self.name, message="Scrolled to bottom")
            if to_top:
                await page.evaluate("window.scrollTo(0, 0)")
                return ToolResponse.ok(tool=self.name, message="Scrolled to top")

            dx, dy = {"up": (0, -amount_px), "down": (0, amount_px),
                       "left": (-amount_px, 0), "right": (amount_px, 0)}.get(direction, (0, amount_px))
            await page.evaluate(f"window.scrollBy({{left: {dx}, top: {dy}, behavior: 'smooth'}})")
            return ToolResponse.ok(tool=self.name, message=f"Scrolled {direction} {amount_px}px")
        except ElementNotFoundError:
            raise
        except Exception as exc:
            return ToolResponse.fail(tool=self.name, message="Scroll failed",
                                      error=str(exc), error_code="scroll_failed")
