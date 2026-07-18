from __future__ import annotations

import time
from abc import ABC, abstractmethod
from typing import Any, List, Optional

from selenium.common.exceptions import (
    NoSuchElementException,
    StaleElementReferenceException,
    TimeoutException,
)
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from ..engine import BrowserManager
from ..exceptions import (
    BrowserAgentError,
    ElementNotFoundError,
    InvalidToolParamsError,
)
from ..logger import get_logger
from ..models import ToolResponse

logger = get_logger(__name__)


def _gen_css_selector(el: WebElement) -> str:
    tag = el.tag_name
    el_id = el.get_attribute("id")
    if el_id:
        return f"#{el_id}"

    classes = el.get_attribute("class")
    selector = tag
    if classes:
        cls_list = ".".join(c for c in classes.split() if c)
        if cls_list:
            selector += f".{cls_list}"

    attrs = ["name", "type", "placeholder", "aria-label", "role", "href", "src"]
    for attr in attrs:
        val = el.get_attribute(attr)
        if val:
            escaped = val.replace('"', '\\"')
            selector += f'[{attr}="{escaped}"]'
            break

    return selector


class BaseTool(ABC):
    name: str = "base_tool"
    description: str = "Base browser automation tool"

    def __init__(self, browser_manager: BrowserManager):
        self.browser = browser_manager
        self.log = get_logger(f"tools.{self.name}")

    @abstractmethod
    def run(self, **params: Any) -> ToolResponse:
        raise NotImplementedError

    def execute(self, **params: Any) -> ToolResponse:
        try:
            self.log.debug("Executing with params=%s", _redact(params))
            response = self.run(**params)
            return response
        except BrowserAgentError as exc:
            self.log.warning("Tool failed (%s): %s", exc.code, exc.message)
            return ToolResponse.fail(
                tool=self.name,
                message=f"{self.name} failed",
                error=exc.message,
                error_code=exc.code,
                data=exc.details or {},
            )
        except TimeoutException as exc:
            self.log.warning("Selenium timeout: %s", exc)
            return ToolResponse.fail(
                tool=self.name,
                message=f"{self.name} timed out",
                error=str(exc),
                error_code="timeout",
            )
        except Exception as exc:
            self.log.exception("Unexpected error in tool %s", self.name)
            return ToolResponse.fail(
                tool=self.name,
                message=f"{self.name} failed unexpectedly",
                error=str(exc),
                error_code="internal_error",
            )

    def get_driver(self, tab_id: Optional[str] = None):
        return self.browser.get_page(tab_id)

    def find_element(
        self,
        tab_id: Optional[str] = None,
        ref: Optional[str] = None,
        selector: Optional[str] = None,
        text: Optional[str] = None,
        role: Optional[str] = None,
        timeout: int = 10,
    ) -> WebElement:
        driver = self.get_driver(tab_id)
        active_tab = tab_id or self.browser.active_tab_id
        by, value = self._resolve_by(active_tab, ref, selector, text, role)

        try:
            element = WebDriverWait(driver, timeout).until(
                EC.presence_of_element_located((by, value))
            )
            return element
        except TimeoutException:
            raise ElementNotFoundError(
                "No element matched the given locator.",
                ref=ref, selector=selector, text=text, role=role,
            )

    def find_elements(
        self,
        tab_id: Optional[str] = None,
        ref: Optional[str] = None,
        selector: Optional[str] = None,
        text: Optional[str] = None,
        role: Optional[str] = None,
    ) -> List[WebElement]:
        driver = self.get_driver(tab_id)
        active_tab = tab_id or self.browser.active_tab_id
        by, value = self._resolve_by(active_tab, ref, selector, text, role)
        return driver.find_elements(by, value)

    def _resolve_by(
        self,
        active_tab: str,
        ref: Optional[str] = None,
        selector: Optional[str] = None,
        text: Optional[str] = None,
        role: Optional[str] = None,
    ):
        if ref:
            css = self.browser.resolve_ref(active_tab, ref)
            if not css:
                raise ElementNotFoundError(
                    f"Unknown element ref '{ref}'. Call 'observe' again to refresh refs.",
                    ref=ref,
                )
            return By.CSS_SELECTOR, css
        elif selector:
            return By.CSS_SELECTOR, selector
        elif role:
            return By.CSS_SELECTOR, f"[role='{role}']"
        elif text:
            return By.XPATH, f".//*[contains(text(), '{text.replace(chr(39), chr(34))}')]"
        else:
            raise InvalidToolParamsError(
                "Provide one of: ref, selector, role, or text to identify the element."
            )


def _redact(params: dict) -> dict:
    redacted = {}
    for k, v in params.items():
        if isinstance(v, str) and len(v) > 200:
            redacted[k] = v[:200] + "...<truncated>"
        else:
            redacted[k] = v
    return redacted
