from ..exceptions import InvalidToolParamsError
from ..models import ToolResponse
from .base import BaseTool


class CloseTool(BaseTool):
    name = "close"

    async def run(self, scope: str = "tab") -> ToolResponse:
        try:
            if scope == "tab":
                active = self.browser.active_tab_id
                if active:
                    new_active = await self.browser.close_tab(active)
                    return ToolResponse.ok(tool=self.name,
                                            message=f"Closed tab {active}",
                                            data={"closed": active, "active_tab": new_active})
                return ToolResponse.ok(tool=self.name, message="No tab to close")
            elif scope == "browser":
                await self.browser.shutdown()
                return ToolResponse.ok(tool=self.name, message="Browser shut down")
            else:
                raise InvalidToolParamsError(f"Unknown close scope '{scope}'. Use: tab, browser")
        except InvalidToolParamsError:
            raise
        except Exception as exc:
            return ToolResponse.fail(tool=self.name, message="Close failed",
                                      error=str(exc), error_code="close_failed")
