from ..exceptions import InvalidToolParamsError, NavigationError
from ..models import ToolResponse
from .base import BaseTool


class NavigateTool(BaseTool):
    name = "navigate"

    async def run(self, action: str, timeout_ms: int = 15000) -> ToolResponse:
        try:
            page = self.get_page()
            if action == "back":
                await page.go_back(timeout=timeout_ms)
            elif action == "forward":
                await page.go_forward(timeout=timeout_ms)
            elif action == "refresh" or action == "reload":
                await page.reload(timeout=timeout_ms)
            else:
                raise InvalidToolParamsError(f"Unknown navigation action '{action}'. Use: back, forward, refresh")
            return ToolResponse.ok(tool=self.name, message=f"Navigation '{action}' completed",
                                    data={"action": action, "url": page.url})
        except (InvalidToolParamsError, NavigationError):
            raise
        except Exception as exc:
            raise NavigationError(f"Navigation '{action}' failed: {exc}") from exc
