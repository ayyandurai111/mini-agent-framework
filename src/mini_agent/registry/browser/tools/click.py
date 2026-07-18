from ..exceptions import ElementNotFoundError
from ..models import ToolResponse
from .base import BaseTool


class ClickTool(BaseTool):
    name = "click"
    description = "Click an element by ref, CSS selector, or text"

    def run(self, ref: str = None, selector: str = None,
            text: str = None, role: str = None,
            button: str = "left", double_click: bool = False,
            timeout_ms: int = 10000) -> ToolResponse:
        try:
            element = self.find_element(ref=ref, selector=selector,
                                        text=text, role=role,
                                        timeout=max(1, timeout_ms // 1000))
            if double_click:
                from selenium.webdriver.common.action_chains import ActionChains
                driver = self.get_driver()
                ActionChains(driver).double_click(element).perform()
            else:
                element.click()
            return ToolResponse.ok(
                tool=self.name,
                message=f"Clicked element ({ref or selector or text or role})",
            )
        except ElementNotFoundError:
            raise
        except Exception as exc:
            raise ElementNotFoundError(f"Click failed: {exc}") from exc
