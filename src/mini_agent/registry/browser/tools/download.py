import os
import time

from ..exceptions import DownloadError, ElementNotFoundError, InvalidToolParamsError
from ..models import ToolResponse
from .base import BaseTool


class DownloadTool(BaseTool):
    name = "download"
    description = "Trigger or list file downloads"

    def run(self, action: str = "trigger", ref: str = None,
            selector: str = None, timeout_ms: int = 30000) -> ToolResponse:
        try:
            if action == "list":
                downloads = self.browser.get_downloads()
                return ToolResponse.ok(tool=self.name,
                                       message=f"{len(downloads)} downloads",
                                       data={"downloads": downloads})
            elif action == "trigger":
                if not ref and not selector:
                    raise InvalidToolParamsError("Provide ref or selector to trigger download")
                element = self.find_element(ref=ref, selector=selector,
                                            timeout=max(1, timeout_ms // 1000))
                before = set(os.listdir(self.browser.downloads_dir))
                element.click()
                time.sleep(2)
                after = set(os.listdir(self.browser.downloads_dir))
                new_files = after - before

                if new_files:
                    fname = list(new_files)[0]
                    path = os.path.join(self.browser.downloads_dir, fname)
                    record = {
                        "suggested_filename": fname,
                        "saved_path": path,
                        "url": self.get_driver().current_url,
                    }
                    self.browser._downloads.append(record)
                    return ToolResponse.ok(tool=self.name,
                                           message=f"Download triggered: {fname}",
                                           data={"filename": fname, "path": path})
                return ToolResponse.ok(tool=self.name, message="Click triggered, no new download detected")

            else:
                raise InvalidToolParamsError(f"Unknown download action '{action}'")
        except (ElementNotFoundError, InvalidToolParamsError, DownloadError):
            raise
        except Exception as exc:
            raise DownloadError(f"Download failed: {exc}") from exc
