from ..models import ToolResponse
from .base import BaseTool, _gen_css_selector

ELEMENT_CATEGORIES = {
    "interactive": [
        "a", "button", "input", "select", "textarea", "details", "summary",
        "menuitem", "[tabindex]", "[contenteditable]",
        "[role=button]", "[role=link]", "[role=checkbox]", "[role=radio]",
        "[role=tab]", "[role=menuitem]", "[role=option]",
    ],
    "inputs": ["input", "textarea", "select", "[contenteditable]"],
    "text": ["p", "h1", "h2", "h3", "h4", "h5", "h6", "span", "li", "label", "td", "th", "blockquote", "pre", "code"],
    "media": ["img", "video", "audio", "canvas", "svg", "picture", "iframe"],
    "structural": ["header", "footer", "nav", "section", "article", "aside", "main", "form", "table"],
}


class ObserveTool(BaseTool):
    name = "observe"
    description = "Scan page for interactive elements with refs"

    def run(self, max_elements: int = 250,
            include_categories: list = None) -> ToolResponse:
        driver = self.get_driver()
        categories = include_categories or list(ELEMENT_CATEGORIES)

        selectors = []
        for cat in categories:
            selectors.extend(ELEMENT_CATEGORIES.get(cat, []))
        if not selectors:
            selectors = [", ".join(ELEMENT_CATEGORIES["interactive"])]

        combined = ", ".join(selectors)
        ref_map = {}
        elements = []

        try:
            items = driver.find_elements("css selector", combined)
            idx = 0
            for el in items:
                if idx >= max_elements:
                    break
                try:
                    tag = el.tag_name
                    text = (el.text or "").strip()[:120]
                    visible = el.is_displayed()
                    loc = el.location
                    size = el.size
                    rect = {"x": loc["x"], "y": loc["y"], "w": size["width"], "h": size["height"]} if size else None

                    attrs = driver.execute_script(
                        "var a={}; for(var attr of arguments[0].attributes) a[attr.name]=attr.value; return a;",
                        el,
                    )

                    css_sel = _gen_css_selector(el)
                    ref = f"e{idx}"
                    ref_map[ref] = css_sel
                    elements.append({
                        "ref": ref,
                        "tag": tag,
                        "text": text[:80] if text else None,
                        "attrs": {k: v for k, v in attrs.items() if k in (
                            "id", "class", "name", "type", "placeholder",
                            "href", "src", "alt", "aria-label", "title",
                            "role", "value", "for",
                        )},
                        "visible": visible,
                        "rect": rect,
                    })
                    idx += 1
                except Exception:
                    continue

            tab_id = self.browser.active_tab_id
            self.browser.set_ref_map(tab_id, ref_map)

            return ToolResponse.ok(
                tool=self.name,
                message=f"Observed {len(elements)} elements",
                data={"elements": elements, "count": len(elements)},
            )
        except Exception as exc:
            return ToolResponse.fail(
                tool=self.name,
                message="Failed to observe page",
                error=str(exc), error_code="observe_failed",
            )
