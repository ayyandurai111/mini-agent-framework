from selenium.webdriver.support.ui import Select as SeleniumSelect

from ..exceptions import ElementNotFoundError, InvalidToolParamsError
from ..models import ToolResponse
from .base import BaseTool


class SelectTool(BaseTool):
    name = "select"
    description = "Select option(s) in a dropdown"

    def run(self, value=None, label=None, index=None,
            ref: str = None, selector: str = None,
            text: str = None, role: str = None,
            timeout_ms: int = 10000) -> ToolResponse:
        if value is None and label is None and index is None:
            raise InvalidToolParamsError("Provide one of: value, label, or index to select.")
        try:
            element = self.find_element(ref=ref, selector=selector,
                                        text=text, role=role,
                                        timeout=max(1, timeout_ms // 1000))
            select = SeleniumSelect(element)
            if value is not None:
                vals = value if isinstance(value, list) else [value]
                select.select_by_value(vals[0] if len(vals) == 1 else vals)
            elif label is not None:
                labels = label if isinstance(label, list) else [label]
                select.select_by_visible_text(labels[0] if len(labels) == 1 else labels)
            elif index is not None:
                indices = index if isinstance(index, list) else [index]
                select.select_by_index(indices[0] if len(indices) == 1 else indices)
            return ToolResponse.ok(tool=self.name, message="Option selected")
        except (ElementNotFoundError, InvalidToolParamsError):
            raise
        except Exception as exc:
            raise ElementNotFoundError(f"Select failed: {exc}") from exc
