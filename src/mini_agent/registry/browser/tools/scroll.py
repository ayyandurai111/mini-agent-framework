from ..exceptions import ElementNotFoundError
from ..models import ToolResponse
from .base import BaseTool


class ScrollTool(BaseTool):
    name = "scroll"
    description = "Scroll page or element into view"

    def run(self, direction: str = "down", amount_px: int = 600,
            to_bottom: bool = False, to_top: bool = False,
            ref: str = None, selector: str = None) -> ToolResponse:
        try:
            driver = self.get_driver()
            if ref or selector:
                element = self.find_element(ref=ref, selector=selector)
                driver.execute_script("arguments[0].scrollIntoViewIfNeeded(true);", element)
                return ToolResponse.ok(tool=self.name, message="Scrolled to element")

            if to_bottom:
                driver.execute_script("window.scrollTo(0, document.body.scrollHeight)")
                return ToolResponse.ok(tool=self.name, message="Scrolled to bottom")
            if to_top:
                driver.execute_script("window.scrollTo(0, 0)")
                return ToolResponse.ok(tool=self.name, message="Scrolled to top")

            dx, dy = {"up": (0, -amount_px), "down": (0, amount_px),
                       "left": (-amount_px, 0), "right": (amount_px, 0)}.get(direction, (0, amount_px))
            driver.execute_script(f"window.scrollBy({{left: {dx}, top: {dy}, behavior: 'smooth'}})")
            return ToolResponse.ok(tool=self.name, message=f"Scrolled {direction} {amount_px}px")
        except ElementNotFoundError:
            raise
        except Exception as exc:
            return ToolResponse.fail(tool=self.name, message="Scroll failed",
                                     error=str(exc), error_code="scroll_failed")
