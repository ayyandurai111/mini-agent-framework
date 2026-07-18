from ..exceptions import ElementNotFoundError, InvalidToolParamsError
from ..models import ToolResponse
from .base import BaseTool


class ReadTool(BaseTool):
    name = "read"
    description = "Read text, HTML, or attributes from page/element"

    def run(self, what: str = "text", ref: str = None,
            selector: str = None, text: str = None,
            attribute: str = None) -> ToolResponse:
        try:
            driver = self.get_driver()
            if what in ("metadata", "title", "url"):
                data = {}
                if what in ("metadata", "title"):
                    data["title"] = driver.title
                if what in ("metadata", "url"):
                    data["url"] = driver.current_url
                return ToolResponse.ok(tool=self.name, message="Page info", data=data)

            element = self.find_element(ref=ref, selector=selector, text=text)
            if what == "text":
                content = element.text
                return ToolResponse.ok(tool=self.name, message="Element text",
                                       data={"text": (content or "").strip()[:2000]})
            elif what == "html":
                html = element.get_attribute("innerHTML")
                return ToolResponse.ok(tool=self.name, message="Element HTML",
                                       data={"html": (html or "")[:3000]})
            elif what == "value":
                val = element.get_attribute("value")
                return ToolResponse.ok(tool=self.name, message="Input value",
                                       data={"value": val or ""})
            elif what == "attribute":
                if not attribute:
                    raise InvalidToolParamsError("'attribute' param required when what='attribute'")
                attr_val = element.get_attribute(attribute)
                return ToolResponse.ok(tool=self.name, message=f"Attribute '{attribute}'",
                                       data={attribute: attr_val})
            else:
                raise InvalidToolParamsError(f"Unknown read type '{what}'")
        except (ElementNotFoundError, InvalidToolParamsError):
            raise
        except Exception as exc:
            raise ElementNotFoundError(f"Read failed: {exc}") from exc
