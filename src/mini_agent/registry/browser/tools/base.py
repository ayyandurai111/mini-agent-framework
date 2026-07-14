from __future__ import annotations

import asyncio
from abc import ABC, abstractmethod
from typing import Any, Optional

from playwright.async_api import Locator, Page, TimeoutError as PlaywrightTimeoutError

from ..engine import BrowserManager
from ..exceptions import (
    BrowserAgentError,
    ElementNotFoundError,
    InvalidToolParamsError,
)
from ..logger import get_logger
from ..models import ToolResponse

logger = get_logger(__name__)


class BaseTool(ABC):
    name: str = "base_tool"

    def __init__(self, browser_manager: BrowserManager):
        self.browser = browser_manager
        self.log = get_logger(f"tools.{self.name}")

    @abstractmethod
    async def run(self, **params: Any) -> ToolResponse:
        raise NotImplementedError

    async def execute(self, **params: Any) -> ToolResponse:
        try:
            self.log.debug("Executing with params=%s", _redact(params))
            response = await self.run(**params)
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
        except PlaywrightTimeoutError as exc:
            self.log.warning("Playwright timeout: %s", exc)
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

    def get_page(self, tab_id: Optional[str] = None) -> Page:
        return self.browser.get_page(tab_id)

    async def resolve_locator(
        self,
        tab_id: Optional[str] = None,
        ref: Optional[str] = None,
        selector: Optional[str] = None,
        text: Optional[str] = None,
        role: Optional[str] = None,
        name: Optional[str] = None,
        nth: int = 0,
    ) -> Locator:
        page = self.get_page(tab_id)
        active_tab = tab_id or self.browser.active_tab_id

        if ref:
            css = self.browser.resolve_ref(active_tab, ref)
            if not css:
                raise ElementNotFoundError(
                    f"Unknown element ref '{ref}'. Call 'observe' again to refresh refs.",
                    ref=ref,
                )
            locator = page.locator(css)
        elif selector:
            locator = page.locator(selector)
        elif role:
            locator = page.get_by_role(role, name=name) if name else page.get_by_role(role)
        elif text:
            locator = page.get_by_text(text, exact=False)
        else:
            raise InvalidToolParamsError(
                "Provide one of: ref, selector, role, or text to identify the element."
            )

        count = await locator.count()
        if count == 0:
            raise ElementNotFoundError(
                "No element matched the given locator.",
                ref=ref, selector=selector, text=text, role=role,
            )
        return locator.nth(nth)


def _redact(params: dict) -> dict:
    redacted = {}
    for k, v in params.items():
        if isinstance(v, str) and len(v) > 200:
            redacted[k] = v[:200] + "...<truncated>"
        else:
            redacted[k] = v
    return redacted


async def retry_async(coro_fn, attempts: int = 3, delay_seconds: float = 0.5, *args, **kwargs):
    last_exc: Optional[Exception] = None
    for attempt in range(1, attempts + 1):
        try:
            return await coro_fn(*args, **kwargs)
        except Exception as exc:
            last_exc = exc
            if attempt < attempts:
                logger.debug("Retry %s/%s after error: %s", attempt, attempts, exc)
                await asyncio.sleep(delay_seconds)
    raise last_exc
