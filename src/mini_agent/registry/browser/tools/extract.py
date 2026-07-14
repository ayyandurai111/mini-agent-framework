from ..exceptions import InvalidToolParamsError
from ..models import ToolResponse
from .base import BaseTool


class ExtractTool(BaseTool):
    name = "extract"

    async def run(self, kind: str = "tables", limit: int = None) -> ToolResponse:
        try:
            page = self.get_page()
            if kind == "tables":
                result = await page.evaluate("""() => {
                    return Array.from(document.querySelectorAll('table')).slice(0, arguments[0] || 5).map(t => ({
                        rows: t.rows.length,
                        headers: Array.from(t.querySelectorAll('th')).map(th => th.textContent.trim()),
                        caption: t.querySelector('caption')?.textContent?.trim() || '',
                    }));
                }""", limit)
                return ToolResponse.ok(tool=self.name,
                                        message=f"Extracted {len(result)} tables",
                                        data={"tables": result})
            elif kind == "links":
                result = await page.evaluate("""(limit) => {
                    return Array.from(document.querySelectorAll('a[href]')).slice(0, limit || 50).map(a => ({
                        text: a.textContent.trim().slice(0, 100),
                        href: a.getAttribute('href'),
                    }));
                }""", limit)
                return ToolResponse.ok(tool=self.name,
                                        message=f"Extracted {len(result)} links",
                                        data={"links": result})
            elif kind == "images":
                result = await page.evaluate("""(limit) => {
                    return Array.from(document.querySelectorAll('img[src]')).slice(0, limit || 50).map(img => ({
                        src: img.getAttribute('src'),
                        alt: img.getAttribute('alt') || '',
                        width: img.naturalWidth,
                        height: img.naturalHeight,
                    }));
                }""", limit)
                return ToolResponse.ok(tool=self.name,
                                        message=f"Extracted {len(result)} images",
                                        data={"images": result})
            elif kind == "forms":
                result = await page.evaluate("""() => {
                    return Array.from(document.querySelectorAll('form')).map(f => ({
                        action: f.getAttribute('action'),
                        method: f.getAttribute('method') || 'get',
                        inputs: Array.from(f.querySelectorAll('input, select, textarea')).map(i => ({
                            name: i.getAttribute('name'),
                            type: i.getAttribute('type') || i.tagName.toLowerCase(),
                        })),
                    }));
                }""")
                return ToolResponse.ok(tool=self.name,
                                        message=f"Extracted {len(result)} forms",
                                        data={"forms": result})
            else:
                raise InvalidToolParamsError(f"Unknown extract kind '{kind}'. Use: tables, links, images, forms")
        except InvalidToolParamsError:
            raise
        except Exception as exc:
            return ToolResponse.fail(tool=self.name, message="Extract failed",
                                      error=str(exc), error_code="extract_failed")
