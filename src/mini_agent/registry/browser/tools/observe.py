from ..models import ToolResponse
from .base import BaseTool

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

    async def run(self, max_elements: int = 250,
                  include_categories: list = None) -> ToolResponse:
        page = self.get_page()
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
            items = await page.query_selector_all(combined)
            idx = 0
            for i, el in enumerate(items):
                if idx >= max_elements:
                    break
                try:
                    tag = await el.evaluate("e => e.tagName.toLowerCase()")
                    text = await el.text_content() or ""
                    text = text.strip()[:120]
                    attrs = await el.evaluate("""e => {
                        const a = {};
                        for (const attr of e.attributes) a[attr.name] = attr.value;
                        return a;
                    }""")
                    visible = await el.is_visible()
                    box = await el.bounding_box()
                    rect = {"x": box["x"], "y": box["y"], "w": box["width"], "h": box["height"]} if box else None

                    ref = f"e{idx}"
                    ref_map[ref] = el  # stored as element handle reference
                    elements.append({
                        "ref": ref,
                        "tag": tag,
                        "text": text[:80] if text else None,
                        "attrs": {k: v for k, v in attrs.items() if k in ("id", "class", "name", "type", "placeholder", "href", "src", "alt", "aria-label", "title", "role", "value", "for")},
                        "visible": visible,
                        "rect": rect,
                    })
                    idx += 1
                except Exception:
                    continue

            await page.evaluate("""ref_map => {
                window.__browser_refs = {};
                for (const [ref, el] of Object.entries(ref_map))
                    window.__browser_refs[ref] = el;
            }""", ref_map)

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
