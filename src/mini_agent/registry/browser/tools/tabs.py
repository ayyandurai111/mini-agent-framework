from ..exceptions import InvalidToolParamsError
from ..models import ToolResponse
from .base import BaseTool


class TabsTool(BaseTool):
    name = "tabs"
    description = "Manage browser tabs (list, open, close, switch)"

    async def run(self, action: str, tab_id: str = None,
                  url: str = None) -> ToolResponse:
        try:
            if action == "list":
                tabs = self.browser.list_tabs()
                return ToolResponse.ok(tool=self.name, message=f"{len(tabs)} tabs",
                                        data={"tabs": tabs, "active_tab": self.browser.active_tab_id})
            elif action in ("open", "new"):
                new_id = await self.browser.open_tab(url)
                return ToolResponse.ok(tool=self.name, message=f"Opened tab {new_id}",
                                        data={"tab_id": new_id})
            elif action == "close":
                if not tab_id:
                    raise InvalidToolParamsError("'tab_id' required for close action")
                active = await self.browser.close_tab(tab_id)
                return ToolResponse.ok(tool=self.name, message=f"Closed tab {tab_id}",
                                        data={"closed": tab_id, "active_tab": active})
            elif action in ("switch", "activate", "focus"):
                if not tab_id:
                    raise InvalidToolParamsError("'tab_id' required for switch action")
                await self.browser.switch_tab(tab_id)
                return ToolResponse.ok(tool=self.name, message=f"Switched to tab {tab_id}",
                                        data={"tab_id": tab_id})
            else:
                raise InvalidToolParamsError(f"Unknown tabs action '{action}'. Use: list, open, close, switch")
        except InvalidToolParamsError:
            raise
        except Exception as exc:
            return ToolResponse.fail(tool=self.name, message=f"Tab operation failed",
                                      error=str(exc), error_code="tab_error")
