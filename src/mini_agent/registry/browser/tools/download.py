from ..exceptions import DownloadError, ElementNotFoundError, InvalidToolParamsError
from ..models import ToolResponse
from .base import BaseTool

import os


class DownloadTool(BaseTool):
    name = "download"
    description = "Trigger or list file downloads"

    async def run(self, action: str = "trigger", ref: str = None,
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
                locator = await self.resolve_locator(ref=ref, selector=selector)
                async with self.browser.get_page().expect_download(timeout=timeout_ms) as info:
                    await locator.click()
                download = await info.value
                suggested = download.suggested_filename or "download"
                dest = os.path.join(self.browser.downloads_dir, suggested)
                await download.save_as(dest)
                return ToolResponse.ok(tool=self.name,
                                        message=f"Download triggered: {suggested}",
                                        data={"filename": suggested, "path": dest, "url": download.url})
            else:
                raise InvalidToolParamsError(f"Unknown download action '{action}'")
        except (ElementNotFoundError, InvalidToolParamsError, DownloadError):
            raise
        except Exception as exc:
            raise DownloadError(f"Download failed: {exc}") from exc
