from ..exceptions import InvalidToolParamsError, NavigationError
from ..models import ToolResponse
from .base import BaseTool


class NavigateTool(BaseTool):
    name = "navigate"
    description = "Browser history navigation (back, forward, refresh)"

    def run(self, action: str, timeout_ms: int = 15000) -> ToolResponse:
        try:
            driver = self.get_driver()
            if action == "back":
                driver.back()
            elif action == "forward":
                driver.forward()
            elif action == "refresh" or action == "reload":
                driver.refresh()
            else:
                raise InvalidToolParamsError(f"Unknown navigation action '{action}'. Use: back, forward, refresh")
            return ToolResponse.ok(tool=self.name, message=f"Navigation '{action}' completed",
                                   data={"action": action, "url": driver.current_url})
        except (InvalidToolParamsError, NavigationError):
            raise
        except Exception as exc:
            raise NavigationError(f"Navigation '{action}' failed: {exc}") from exc
