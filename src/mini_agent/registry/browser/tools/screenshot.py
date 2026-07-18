import os
from datetime import datetime

from ..exceptions import ElementNotFoundError
from ..models import ToolResponse
from .base import BaseTool


class ScreenshotTool(BaseTool):
    name = "screenshot"
    description = "Capture page or element screenshot"

    def run(self, full_page: bool = False, file_name: str = None,
            ref: str = None, selector: str = None) -> ToolResponse:
        try:
            dest_dir = self.browser.screenshots_dir
            os.makedirs(dest_dir, exist_ok=True)
            fname = file_name or f"screenshot_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
            path = os.path.join(dest_dir, fname)

            if ref or selector:
                element = self.find_element(ref=ref, selector=selector)
                element.screenshot(path)
            else:
                driver = self.get_driver()
                if full_page:
                    body = driver.find_element("tag name", "body")
                    body.screenshot(path)
                else:
                    driver.save_screenshot(path)

            return ToolResponse.ok(tool=self.name, message="Screenshot saved",
                                   data={"path": path, "file_name": fname})
        except ElementNotFoundError:
            raise
        except Exception as exc:
            return ToolResponse.fail(tool=self.name, message="Screenshot failed",
                                     error=str(exc), error_code="screenshot_failed")
