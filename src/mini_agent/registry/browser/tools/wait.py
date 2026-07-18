import time

from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from ..exceptions import BrowserTimeoutError, ElementNotFoundError, InvalidToolParamsError
from ..models import ToolResponse
from .base import BaseTool


class WaitTool(BaseTool):
    name = "wait"
    description = "Wait for load state, element, or timeout"

    def run(self, for_: str = "load_state", load_state: str = "load",
            milliseconds: int = 1000, ref: str = None,
            selector: str = None, timeout_ms: int = 30000) -> ToolResponse:
        try:
            driver = self.get_driver()
            timeout = max(1, timeout_ms // 1000)

            if for_ == "load_state":
                self.browser.wait_for_load(timeout_ms=timeout_ms)
                return ToolResponse.ok(tool=self.name, message=f"Load state '{load_state}' reached")
            elif for_ == "selector":
                if not selector:
                    raise InvalidToolParamsError("'selector' param required when for_='selector'")
                WebDriverWait(driver, timeout).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, selector))
                )
                return ToolResponse.ok(tool=self.name, message=f"Selector '{selector}' appeared")
            elif for_ == "ref" or for_ == "element":
                self.find_element(ref=ref, selector=selector, timeout=timeout)
                return ToolResponse.ok(tool=self.name, message="Element visible")
            elif for_ == "timeout":
                time.sleep(milliseconds / 1000)
                return ToolResponse.ok(tool=self.name, message=f"Waited {milliseconds}ms")
            elif for_ == "navigation":
                WebDriverWait(driver, timeout).until(
                    lambda d: d.execute_script("return document.readyState") == "complete"
                )
                return ToolResponse.ok(tool=self.name, message="Navigation completed")
            else:
                raise InvalidToolParamsError(f"Unknown wait type '{for_}'")
        except (ElementNotFoundError, InvalidToolParamsError, BrowserTimeoutError):
            raise
        except Exception as exc:
            raise BrowserTimeoutError(f"Wait failed: {exc}") from exc
