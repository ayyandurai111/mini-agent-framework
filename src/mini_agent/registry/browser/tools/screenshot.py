from ..exceptions import ElementNotFoundError
from ..models import ToolResponse
from .base import BaseTool

import os
from datetime import datetime


class ScreenshotTool(BaseTool):
    name = "screenshot"
    description = "Capture page or element screenshot"

    async def run(self, full_page: bool = False, file_name: str = None,
                  ref: str = None, selector: str = None) -> ToolResponse:
        try:
            dest_dir = self.browser.screenshots_dir
            os.makedirs(dest_dir, exist_ok=True)
            fname = file_name or f"screenshot_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
            path = os.path.join(dest_dir, fname)

            if ref or selector:
                locator = await self.resolve_locator(ref=ref, selector=selector)
                await locator.screenshot(path=path)
            else:
                page = self.get_page()
                await page.screenshot(path=path, full_page=full_page)

            return ToolResponse.ok(tool=self.name, message=f"Screenshot saved",
                                    data={"path": path, "file_name": fname})
        except ElementNotFoundError:
            raise
        except Exception as exc:
            return ToolResponse.fail(tool=self.name, message="Screenshot failed",
                                      error=str(exc), error_code="screenshot_failed")
