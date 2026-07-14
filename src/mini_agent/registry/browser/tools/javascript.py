from ..exceptions import ScriptExecutionError
from ..models import ToolResponse
from .base import BaseTool


class ExecuteJSTool(BaseTool):
    name = "execute_js"

    async def run(self, code: str, timeout_ms: int = 10000) -> ToolResponse:
        try:
            page = self.get_page()
            result = await page.evaluate(code)
            return ToolResponse.ok(tool=self.name, message="JS executed",
                                    data={"result": str(result)[:2000] if result is not None else None,
                                          "result_type": type(result).__name__})
        except Exception as exc:
            raise ScriptExecutionError(f"JS execution failed: {exc}") from exc
