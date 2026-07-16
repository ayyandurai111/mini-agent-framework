from ..exceptions import ElementNotFoundError, InvalidToolParamsError
from ..models import ToolResponse
from .base import BaseTool


class SelectTool(BaseTool):
    name = "select"
    description = "Select option(s) in a dropdown"

    async def run(self, value=None, label=None, index=None,
                  ref: str = None, selector: str = None,
                  text: str = None, role: str = None,
                  timeout_ms: int = 10000) -> ToolResponse:
        if value is None and label is None and index is None:
            raise InvalidToolParamsError("Provide one of: value, label, or index to select.")
        try:
            locator = await self.resolve_locator(ref=ref, selector=selector,
                                                  text=text, role=role)
            if value is not None:
                selected = value if isinstance(value, list) else [value]
                await locator.select_option(value=selected, timeout=timeout_ms)
            elif label is not None:
                labels = label if isinstance(label, list) else [label]
                await locator.select_option(label=labels, timeout=timeout_ms)
            elif index is not None:
                indices = index if isinstance(index, list) else [index]
                await locator.select_option(index=indices, timeout=timeout_ms)
            return ToolResponse.ok(tool=self.name, message="Option selected")
        except (ElementNotFoundError, InvalidToolParamsError):
            raise
        except Exception as exc:
            raise ElementNotFoundError(f"Select failed: {exc}") from exc
