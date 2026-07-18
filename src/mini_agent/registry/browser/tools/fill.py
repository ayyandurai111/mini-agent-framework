import time

from ..exceptions import ElementNotFoundError
from ..models import ToolResponse
from .base import BaseTool


class FillTool(BaseTool):
    name = "fill"
    description = "Type text into an input/textarea element"

    def run(self, value: str, ref: str = None, selector: str = None,
            text: str = None, role: str = None,
            clear_first: bool = True, press_enter: bool = False,
            simulate_typing: bool = False,
            timeout_ms: int = 10000) -> ToolResponse:
        try:
            element = self.find_element(ref=ref, selector=selector,
                                        text=text, role=role,
                                        timeout=max(1, timeout_ms // 1000))
            if clear_first:
                element.clear()
                time.sleep(0.1)
            if simulate_typing:
                for ch in value:
                    element.send_keys(ch)
                    time.sleep(0.05)
            else:
                element.send_keys(value)
            if press_enter:
                element.send_keys("\n")
            return ToolResponse.ok(
                tool=self.name,
                message=f"Filled '{value[:50]}' into element",
                data={"value_preview": value[:100]},
            )
        except ElementNotFoundError:
            raise
        except Exception as exc:
            raise ElementNotFoundError(f"Fill failed: {exc}") from exc
