from ..exceptions import ElementNotFoundError
from ..models import ToolResponse
from .base import BaseTool


class CheckTool(BaseTool):
    name = "check"
    description = "Check or uncheck a checkbox/radio button"

    def run(self, checked: bool = True, ref: str = None,
            selector: str = None, text: str = None,
            role: str = None, timeout_ms: int = 10000) -> ToolResponse:
        try:
            element = self.find_element(ref=ref, selector=selector,
                                        text=text, role=role,
                                        timeout=max(1, timeout_ms // 1000))
            currently_checked = element.is_selected()
            if checked and not currently_checked:
                element.click()
            elif not checked and currently_checked:
                element.click()
            state = "checked" if checked else "unchecked"
            return ToolResponse.ok(tool=self.name, message=f"Element {state}")
        except ElementNotFoundError:
            raise
        except Exception as exc:
            raise ElementNotFoundError(f"Check failed: {exc}") from exc
