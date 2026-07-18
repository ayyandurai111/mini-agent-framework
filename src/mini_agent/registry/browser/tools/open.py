from ..exceptions import NavigationError
from ..models import ToolResponse
from .base import BaseTool


class OpenTool(BaseTool):
    name = "open"
    description = "Navigate to a URL in the browser"

    def run(self, url: str, new_tab: bool = False,
            wait_until: str = "domcontentloaded",
            timeout_ms: int = 30000) -> ToolResponse:
        try:
            if new_tab:
                tab_id = self.browser.open_tab(url)
            else:
                driver = self.get_driver()
                driver.get(url)
                tab_id = self.browser.active_tab_id
            if wait_until in ("domcontentloaded", "load", "networkidle"):
                self.browser.wait_for_load(timeout_ms=timeout_ms)
            return ToolResponse.ok(
                tool=self.name,
                message=f"Opened {url}",
                data={"url": url, "tab_id": tab_id},
            )
        except Exception as exc:
            raise NavigationError(f"Failed to open {url}: {exc}") from exc
