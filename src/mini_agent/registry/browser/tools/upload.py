from ..exceptions import ElementNotFoundError, InvalidToolParamsError
from ..models import ToolResponse
from .base import BaseTool


class UploadTool(BaseTool):
    name = "upload"
    description = "Upload file(s) to an input element"

    def run(self, file_paths, ref: str = None,
            selector: str = None, timeout_ms: int = 15000) -> ToolResponse:
        try:
            element = self.find_element(ref=ref, selector=selector,
                                        timeout=max(1, timeout_ms // 1000))
            paths = file_paths if isinstance(file_paths, list) else [file_paths]
            element.send_keys("\n".join(paths))
            return ToolResponse.ok(tool=self.name, message=f"Uploaded {len(paths)} file(s)",
                                   data={"files": paths})
        except (ElementNotFoundError, InvalidToolParamsError):
            raise
        except Exception as exc:
            raise ElementNotFoundError(f"Upload failed: {exc}") from exc
