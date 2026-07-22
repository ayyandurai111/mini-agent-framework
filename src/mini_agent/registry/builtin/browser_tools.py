"""
registry/builtin/browser_tools.py
---------------------------------
Browser automation tools wrapping undetected-chromedriver (Selenium)
into individual framework Tool objects.

Install:
    pip install mini_agent[browser]
"""

import atexit
import subprocess
import sys
import threading

from ..tools import Tool


_lock = threading.Lock()
_agent = None
_IMPORT_ERROR = None
_headless_mode = True


def _shutdown_browser():
    global _agent
    mgr = _agent
    if mgr is None:
        return
    _agent = None
    try:
        mgr.shutdown()
    except Exception:
        pass


atexit.register(_shutdown_browser)


def init_browser(headless: bool = True):
    """Configure browser mode before registering BROWSER_TOOLS.

    Call BEFORE register_tools(BROWSER_TOOLS), or to restart with a
    different setting at any point.

    Parameters
    ----------
    headless : bool
        True  -> invisible browser (default)
        False -> visible GUI window
    """
    global _headless_mode
    _shutdown_browser()
    _headless_mode = headless


def _ensure_browser():
    global _agent, _IMPORT_ERROR
    if _agent is not None:
        return
    if _IMPORT_ERROR:
        raise _IMPORT_ERROR

    with _lock:
        if _agent is not None:
            return
        try:
            from ..browser.session import BrowserSession
        except ImportError:
            _IMPORT_ERROR = ImportError(
                "Browser tools require undetected-chromedriver. "
                "Install: pip install mini_agent[browser]"
            )
            raise _IMPORT_ERROR

        try:
            _agent = BrowserSession(headless=_headless_mode)
            _agent.start()
        except Exception as e:
            error_msg = str(e).lower()
            if "executable doesn't exist" in error_msg or "browser" in error_msg:
                _IMPORT_ERROR = e
                raise
            _IMPORT_ERROR = e
            raise


def _browser_call(tool_name: str, **params) -> str:
    try:
        _ensure_browser()
        result = _agent.call(tool_name, **params)
        if isinstance(result, dict):
            lines = []
            for k, v in result.items():
                if k == "data" and isinstance(v, dict):
                    for dk, dv in v.items():
                        lines.append(f"  {dk}: {str(dv)[:300]}")
                else:
                    lines.append(f"  {k}: {str(v)[:300]}")
            return "\n".join(lines) if lines else str(result)
        return str(result)
    except ImportError as e:
        return str(e)
    except Exception as exc:
        return f"Browser error: {exc}"


def browser_open(url: str, new_tab: bool = False, wait_until: str = "domcontentloaded", timeout_ms: int = 30000) -> str:
    return _browser_call("open", url=url, new_tab=new_tab, wait_until=wait_until, timeout_ms=timeout_ms)


def browser_observe(max_elements: int = 250, include_categories: list = None) -> str:
    return _browser_call("observe", max_elements=max_elements, include_categories=include_categories)


def browser_click(ref: str = None, selector: str = None, text: str = None,
                 role: str = None, button: str = "left", double_click: bool = False,
                 timeout_ms: int = 10000) -> str:
    return _browser_call("click", ref=ref, selector=selector, text=text, role=role,
                         button=button, double_click=double_click, timeout_ms=timeout_ms)


def browser_fill(value: str, ref: str = None, selector: str = None, text: str = None,
                 role: str = None, clear_first: bool = True, press_enter: bool = False,
                 simulate_typing: bool = False, timeout_ms: int = 10000) -> str:
    return _browser_call("fill", value=value, ref=ref, selector=selector, text=text,
                         role=role, clear_first=clear_first, press_enter=press_enter,
                         simulate_typing=simulate_typing, timeout_ms=timeout_ms)


def browser_select(value=None, label=None, index=None, ref: str = None,
                   selector: str = None, text: str = None, role: str = None,
                   timeout_ms: int = 10000) -> str:
    return _browser_call("select", value=value, label=label, index=index,
                         ref=ref, selector=selector, text=text, role=role,
                         timeout_ms=timeout_ms)


def browser_check(checked: bool = True, ref: str = None, selector: str = None,
                  text: str = None, role: str = None, timeout_ms: int = 10000) -> str:
    return _browser_call("check", checked=checked, ref=ref, selector=selector,
                         text=text, role=role, timeout_ms=timeout_ms)


def browser_scroll(direction: str = "down", amount_px: int = 600,
                   to_bottom: bool = False, to_top: bool = False,
                   ref: str = None, selector: str = None) -> str:
    return _browser_call("scroll", direction=direction, amount_px=amount_px,
                         to_bottom=to_bottom, to_top=to_top,
                         ref=ref, selector=selector)


def browser_wait(for_: str = "load_state", load_state: str = "load",
                 milliseconds: int = 1000, ref: str = None,
                 selector: str = None, timeout_ms: int = 30000) -> str:
    return _browser_call("wait", for_=for_, load_state=load_state,
                         milliseconds=milliseconds, ref=ref,
                         selector=selector, timeout_ms=timeout_ms)


def browser_navigate(action: str, timeout_ms: int = 15000) -> str:
    return _browser_call("navigate", action=action, timeout_ms=timeout_ms)


def browser_tabs(action: str, tab_id: str = None, url: str = None) -> str:
    return _browser_call("tabs", action=action, tab_id=tab_id, url=url)


def browser_upload(file_paths, ref: str = None, selector: str = None,
                   timeout_ms: int = 15000) -> str:
    return _browser_call("upload", file_paths=file_paths, ref=ref,
                         selector=selector, timeout_ms=timeout_ms)


def browser_download(action: str = "trigger", ref: str = None,
                     selector: str = None, timeout_ms: int = 30000) -> str:
    return _browser_call("download", action=action, ref=ref,
                         selector=selector, timeout_ms=timeout_ms)


def browser_dialog(action: str = "last", handle: str = "dismiss",
                   prompt_text: str = None) -> str:
    return _browser_call("dialog", action=action, handle=handle,
                         prompt_text=prompt_text)


def browser_read(what: str = "text", ref: str = None, selector: str = None,
                 text: str = None, attribute: str = None) -> str:
    return _browser_call("read", what=what, ref=ref, selector=selector,
                         text=text, attribute=attribute)


def browser_extract(kind: str = "tables", limit: int = None) -> str:
    return _browser_call("extract", kind=kind, limit=limit)


def browser_execute_js(code: str, timeout_ms: int = 10000) -> str:
    return _browser_call("execute_js", code=code, timeout_ms=timeout_ms)


def browser_storage(store: str = "cookies", action: str = "get",
                    key: str = None, value: str = None) -> str:
    return _browser_call("storage", store=store, action=action,
                         key=key, value=value)


def browser_screenshot(full_page: bool = False, file_name: str = None,
                       ref: str = None, selector: str = None) -> str:
    return _browser_call("screenshot", full_page=full_page, file_name=file_name,
                         ref=ref, selector=selector)


def browser_close(scope: str = "tab") -> str:
    return _browser_call("close", scope=scope)


BROWSER_TOOLS = [
    Tool(name="browser_open", description="Navigate to a URL in the browser", func=browser_open,
         parameters={"url": "URL to navigate to", "new_tab": "open in new tab (bool)", "wait_until": "load state to wait for (load|domcontentloaded|networkidle)", "timeout_ms": "timeout in ms"},
         requires_approval=True),
    Tool(name="browser_observe", description="Scan the page for interactive elements and return a structured list with refs", func=browser_observe,
         parameters={"max_elements": "max items to return (int)", "include_categories": "filter by element categories (list)"},
         requires_approval=True),
    Tool(name="browser_click", description="Click an element by ref, CSS selector, or text", func=browser_click,
         parameters={"ref": "element ref from observe (e.g. e3)", "selector": "CSS selector", "text": "visible text", "role": "ARIA role", "button": "mouse button (left|right|middle)", "double_click": "double-click (bool)", "timeout_ms": "timeout in ms"},
         requires_approval=True),
    Tool(name="browser_fill", description="Type text into an input/textarea element", func=browser_fill,
         parameters={"value": "text to type", "ref": "element ref from observe", "selector": "CSS selector", "text": "visible text", "role": "ARIA role", "clear_first": "clear field before typing (bool)", "press_enter": "press Enter after typing (bool)", "simulate_typing": "type character by character (bool)", "timeout_ms": "timeout in ms"},
         requires_approval=True),
    Tool(name="browser_select", description="Select option(s) in a dropdown", func=browser_select,
         parameters={"value": "option value to select", "label": "option label to select", "index": "option index to select", "ref": "element ref", "selector": "CSS selector", "text": "visible text", "role": "ARIA role", "timeout_ms": "timeout in ms"},
         requires_approval=True),
    Tool(name="browser_check", description="Check or uncheck a checkbox/radio button", func=browser_check,
         parameters={"checked": "target state (bool)", "ref": "element ref", "selector": "CSS selector", "text": "visible text", "role": "ARIA role", "timeout_ms": "timeout in ms"},
         requires_approval=True),
    Tool(name="browser_scroll", description="Scroll the page or an element into view", func=browser_scroll,
         parameters={"direction": "scroll direction (up|down|left|right)", "amount_px": "pixels to scroll", "to_bottom": "scroll to page bottom (bool)", "to_top": "scroll to page top (bool)", "ref": "element ref to scroll to", "selector": "CSS selector to scroll to"},
         requires_approval=True),
    Tool(name="browser_wait", description="Wait for load state, element, or timeout", func=browser_wait,
         parameters={"for_": "wait type (load_state|selector|ref|timeout|navigation)", "load_state": "target load state", "milliseconds": "ms to wait (when for_=timeout)", "ref": "element ref to wait for", "selector": "CSS selector to wait for", "timeout_ms": "max wait time"},
         requires_approval=True),
    Tool(name="browser_navigate", description="Browser history navigation (back, forward, refresh)", func=browser_navigate,
         parameters={"action": "navigation action (back|forward|refresh)", "timeout_ms": "timeout in ms"},
         requires_approval=True),
    Tool(name="browser_tabs", description="Manage browser tabs (open, close, switch, list)", func=browser_tabs,
         parameters={"action": "tab action (open|close|switch|list)", "tab_id": "target tab id", "url": "URL to open in new tab"},
         requires_approval=True),
    Tool(name="browser_upload", description="Upload file(s) to an input element", func=browser_upload,
         parameters={"file_paths": "file path(s) to upload", "ref": "element ref", "selector": "CSS selector", "timeout_ms": "timeout in ms"},
         requires_approval=True),
    Tool(name="browser_download", description="Trigger or list file downloads", func=browser_download,
         parameters={"action": "download action (trigger|list)", "ref": "element ref to trigger download", "selector": "CSS selector", "timeout_ms": "timeout in ms"},
         requires_approval=True),
    Tool(name="browser_dialog", description="Configure or inspect browser dialogs (alert/confirm/prompt)", func=browser_dialog,
         parameters={"action": "dialog action (last|configure)", "handle": "how to handle (accept|dismiss)", "prompt_text": "text for prompt dialogs"},
         requires_approval=True),
    Tool(name="browser_read", description="Read text, HTML, or attributes from the page or element", func=browser_read,
         parameters={"what": "what to read (text|html|attribute|value|metadata|title|url)", "ref": "element ref", "selector": "CSS selector", "text": "visible text", "attribute": "attribute name (when what=attribute)"},
         requires_approval=True),
    Tool(name="browser_extract", description="Extract structured data from page (tables, links, images, forms)", func=browser_extract,
         parameters={"kind": "data type (tables|links|images|forms)", "limit": "max items to return"},
         requires_approval=True),
    Tool(name="browser_execute_js", description="Run JavaScript in the page context", func=browser_execute_js,
         parameters={"code": "JavaScript code to execute", "timeout_ms": "timeout in ms"},
         requires_approval=True),
    Tool(name="browser_storage", description="Manage cookies, localStorage, or sessionStorage", func=browser_storage,
         parameters={"store": "storage type (cookies|local|session)", "action": "action (get|set|clear|delete)", "key": "storage key", "value": "storage value"},
         requires_approval=True),
    Tool(name="browser_screenshot", description="Capture a page or element screenshot", func=browser_screenshot,
         parameters={"full_page": "capture full page (bool)", "file_name": "output filename", "ref": "element ref to screenshot", "selector": "CSS selector"},
         requires_approval=True),
    Tool(name="browser_close", description="Close current tab or shut down the browser", func=browser_close,
         parameters={"scope": "close scope (tab|browser)"},
         requires_approval=True),
]
