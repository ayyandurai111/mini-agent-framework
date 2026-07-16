from ..exceptions import InvalidToolParamsError, StorageError
from ..models import ToolResponse
from .base import BaseTool


class StorageTool(BaseTool):
    name = "storage"
    description = "Manage cookies, localStorage, or sessionStorage"

    async def run(self, store: str = "cookies", action: str = "get",
                  key: str = None, value: str = None) -> ToolResponse:
        try:
            page = self.get_page()
            context = self.browser._context

            if store == "cookies":
                if action == "get":
                    cookies = await context.cookies()
                    return ToolResponse.ok(tool=self.name,
                                            message=f"{len(cookies)} cookies",
                                            data={"cookies": cookies})
                elif action == "clear":
                    await context.clear_cookies()
                    return ToolResponse.ok(tool=self.name, message="Cookies cleared")
                else:
                    raise InvalidToolParamsError(f"Cookie action '{action}' not supported")

            js_store = {"local": "localStorage", "session": "sessionStorage"}.get(store)
            if not js_store:
                raise InvalidToolParamsError(f"Unknown store '{store}'. Use: cookies, local, session")

            if action == "get":
                if key:
                    val = await page.evaluate(f"({js_store}).getItem(arguments[0])", key)
                    return ToolResponse.ok(tool=self.name, message=f"Value for '{key}'",
                                            data={"key": key, "value": val})
                else:
                    data = await page.evaluate(f"JSON.stringify({{... {js_store}}})")
                    import json
                    return ToolResponse.ok(tool=self.name, message="Storage data",
                                            data={"items": json.loads(data)})
            elif action == "set":
                if not key:
                    raise InvalidToolParamsError("'key' required for set action")
                await page.evaluate(f"({js_store}).setItem(arguments[0], arguments[1])", key, value or "")
                return ToolResponse.ok(tool=self.name, message=f"Set '{key}'")
            elif action == "delete":
                if not key:
                    raise InvalidToolParamsError("'key' required for delete action")
                await page.evaluate(f"({js_store}).removeItem(arguments[0])", key)
                return ToolResponse.ok(tool=self.name, message=f"Deleted '{key}'")
            elif action == "clear":
                await page.evaluate(f"({js_store}).clear()")
                return ToolResponse.ok(tool=self.name, message=f"{store}Storage cleared")
            else:
                raise InvalidToolParamsError(f"Unknown action '{action}' for {store}")
        except (InvalidToolParamsError, StorageError):
            raise
        except Exception as exc:
            raise StorageError(f"Storage operation failed: {exc}") from exc
