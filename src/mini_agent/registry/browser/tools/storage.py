import json

from ..exceptions import InvalidToolParamsError, StorageError
from ..models import ToolResponse
from .base import BaseTool


class StorageTool(BaseTool):
    name = "storage"
    description = "Manage cookies, localStorage, or sessionStorage"

    def run(self, store: str = "cookies", action: str = "get",
            key: str = None, value: str = None) -> ToolResponse:
        try:
            driver = self.get_driver()

            if store == "cookies":
                if action == "get":
                    cookies = driver.get_cookies()
                    return ToolResponse.ok(tool=self.name,
                                           message=f"{len(cookies)} cookies",
                                           data={"cookies": cookies})
                elif action == "clear":
                    driver.delete_all_cookies()
                    return ToolResponse.ok(tool=self.name, message="Cookies cleared")
                else:
                    raise InvalidToolParamsError(f"Cookie action '{action}' not supported")

            js_store = {"local": "localStorage", "session": "sessionStorage"}.get(store)
            if not js_store:
                raise InvalidToolParamsError(f"Unknown store '{store}'. Use: cookies, local, session")

            if action == "get":
                if key:
                    val = driver.execute_script(f"return {js_store}.getItem(arguments[0])", key)
                    return ToolResponse.ok(tool=self.name, message=f"Value for '{key}'",
                                           data={"key": key, "value": val})
                else:
                    data = driver.execute_script(f"return JSON.stringify({{... {js_store}}})")
                    return ToolResponse.ok(tool=self.name, message="Storage data",
                                           data={"items": json.loads(data)})
            elif action == "set":
                if not key:
                    raise InvalidToolParamsError("'key' required for set action")
                driver.execute_script(f"{js_store}.setItem(arguments[0], arguments[1])", key, value or "")
                return ToolResponse.ok(tool=self.name, message=f"Set '{key}'")
            elif action == "delete":
                if not key:
                    raise InvalidToolParamsError("'key' required for delete action")
                driver.execute_script(f"{js_store}.removeItem(arguments[0])", key)
                return ToolResponse.ok(tool=self.name, message=f"Deleted '{key}'")
            elif action == "clear":
                driver.execute_script(f"{js_store}.clear()")
                return ToolResponse.ok(tool=self.name, message=f"{store}Storage cleared")
            else:
                raise InvalidToolParamsError(f"Unknown action '{action}' for {store}")
        except (InvalidToolParamsError, StorageError):
            raise
        except Exception as exc:
            raise StorageError(f"Storage operation failed: {exc}") from exc
