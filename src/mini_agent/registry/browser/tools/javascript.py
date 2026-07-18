from ..exceptions import ScriptExecutionError
from ..models import ToolResponse
from .base import BaseTool


class ExecuteJSTool(BaseTool):
    name = "execute_js"
    description = "Run JavaScript in the page context"

    def run(self, code: str, timeout_ms: int = 10000) -> ToolResponse:
        try:
            driver = self.get_driver()
            result = driver.execute_script(code)
            return ToolResponse.ok(tool=self.name, message="JS executed",
                                   data={"result": str(result)[:2000] if result is not None else None,
                                         "result_type": type(result).__name__})
        except Exception as exc:
            raise ScriptExecutionError(f"JS execution failed: {exc}") from exc
