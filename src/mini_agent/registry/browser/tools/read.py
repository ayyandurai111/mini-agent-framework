from ..exceptions import ElementNotFoundError, InvalidToolParamsError
from ..models import ToolResponse
from .base import BaseTool


class ReadTool(BaseTool):
    name = "read"

    async def run(self, what: str = "text", ref: str = None,
                  selector: str = None, text: str = None,
                  attribute: str = None) -> ToolResponse:
        try:
            page = self.get_page()
            if what in ("metadata", "title", "url"):
                data = {}
                if what in ("metadata", "title"):
                    data["title"] = await page.title()
                if what in ("metadata", "url"):
                    data["url"] = page.url
                return ToolResponse.ok(tool=self.name, message="Page info", data=data)

            locator = await self.resolve_locator(ref=ref, selector=selector, text=text)
            if what == "text":
                content = await locator.text_content()
                return ToolResponse.ok(tool=self.name, message="Element text",
                                        data={"text": (content or "").strip()[:2000]})
            elif what == "html":
                html = await locator.inner_html()
                return ToolResponse.ok(tool=self.name, message="Element HTML",
                                        data={"html": html[:3000]})
            elif what == "value":
                val = await locator.input_value()
                return ToolResponse.ok(tool=self.name, message="Input value",
                                        data={"value": val})
            elif what == "attribute":
                if not attribute:
                    raise InvalidToolParamsError("'attribute' param required when what='attribute'")
                attr_val = await locator.get_attribute(attribute)
                return ToolResponse.ok(tool=self.name, message=f"Attribute '{attribute}'",
                                        data={attribute: attr_val})
            else:
                raise InvalidToolParamsError(f"Unknown read type '{what}'")
        except (ElementNotFoundError, InvalidToolParamsError):
            raise
        except Exception as exc:
            raise ElementNotFoundError(f"Read failed: {exc}") from exc
