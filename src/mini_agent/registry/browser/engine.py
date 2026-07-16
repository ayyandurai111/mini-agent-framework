from __future__ import annotations

import asyncio
import os
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from playwright.async_api import (
    async_playwright,
    Browser,
    BrowserContext,
    Dialog,
    Download,
    Page,
    Playwright,
    TimeoutError as PlaywrightTimeoutError,
)

from .exceptions import (
    BrowserNotStartedError,
    BrowserTimeoutError,
    TabNotFoundError,
)
from .logger import get_logger

logger = get_logger(__name__)

DEFAULT_VIEWPORT = {"width": 1366, "height": 768}
DEFAULT_TIMEOUT_MS = 30_000

CLOUD_SAFE_LAUNCH_ARGS = [
    "--no-sandbox",
    "--disable-setuid-sandbox",
    "--disable-dev-shm-usage",
    "--disable-gpu",
    "--disable-extensions",
    "--disable-background-networking",
]


@dataclass
class DialogPolicy:
    action: str = "dismiss"
    prompt_text: Optional[str] = None
    persist: bool = True


@dataclass
class DialogRecord:
    dialog_type: str
    message: str
    default_value: Optional[str]
    action_taken: str
    tab_id: str


@dataclass
class TabState:
    page: Page
    tab_id: str
    dialog_policy: DialogPolicy = field(default_factory=DialogPolicy)
    last_dialog: Optional[DialogRecord] = None
    last_ref_map: Dict[str, str] = field(default_factory=dict)


class BrowserManager:
    def __init__(
        self,
        headless: bool = True,
        browser_type: str = "chromium",
        downloads_dir: str = "./downloads",
        screenshots_dir: str = "./screenshots",
        viewport: Optional[Dict[str, int]] = None,
        user_agent: Optional[str] = None,
        default_timeout_ms: int = DEFAULT_TIMEOUT_MS,
        slow_mo_ms: int = 0,
        extra_launch_args: Optional[List[str]] = None,
        proxy: Optional[Dict[str, str]] = None,
    ):
        self.headless = headless
        self.browser_type = browser_type
        self.downloads_dir = os.path.abspath(downloads_dir)
        self.screenshots_dir = os.path.abspath(screenshots_dir)
        self.viewport = viewport or DEFAULT_VIEWPORT
        self.user_agent = user_agent
        self.default_timeout_ms = default_timeout_ms
        self.slow_mo_ms = slow_mo_ms
        self.launch_args = extra_launch_args or CLOUD_SAFE_LAUNCH_ARGS
        self.proxy = proxy

        self._playwright: Optional[Playwright] = None
        self._browser: Optional[Browser] = None
        self._context: Optional[BrowserContext] = None
        self._tabs: Dict[str, TabState] = {}
        self._active_tab_id: Optional[str] = None
        self._tab_counter = 0
        self._downloads: List[Dict[str, Any]] = []
        self._start_lock = asyncio.Lock()

    async def start(self) -> None:
        async with self._start_lock:
            if self._browser is not None:
                return

            os.makedirs(self.downloads_dir, exist_ok=True)
            os.makedirs(self.screenshots_dir, exist_ok=True)

            self._playwright = await async_playwright().start()
            launcher = getattr(self._playwright, self.browser_type)

            launch_kwargs: Dict[str, Any] = dict(
                headless=self.headless,
                args=self.launch_args,
                slow_mo=self.slow_mo_ms,
            )
            if self.proxy:
                launch_kwargs["proxy"] = self.proxy

            self._browser = await launcher.launch(**launch_kwargs)
            self._context = await self._browser.new_context(
                viewport=self.viewport,
                user_agent=self.user_agent,
                accept_downloads=True,
            )
            self._context.set_default_timeout(self.default_timeout_ms)
            self._context.set_default_navigation_timeout(self.default_timeout_ms)

            await self.open_tab()
            logger.info(
                "Browser started (engine=%s, headless=%s, viewport=%s)",
                self.browser_type,
                self.headless,
                self.viewport,
            )

    async def shutdown(self) -> None:
        try:
            if self._context is not None:
                await self._context.close()
        except Exception:
            logger.exception("Error closing browser context")
        try:
            if self._browser is not None:
                await self._browser.close()
        except Exception:
            logger.exception("Error closing browser")
        try:
            if self._playwright is not None:
                await self._playwright.stop()
        except Exception:
            logger.exception("Error stopping playwright")

        self._browser = None
        self._context = None
        self._playwright = None
        self._tabs.clear()
        self._active_tab_id = None
        logger.info("Browser shut down")

    def _ensure_started(self) -> None:
        if self._context is None:
            raise BrowserNotStartedError(
                "Browser has not been started. Call agent.start() first."
            )

    async def open_tab(self, url: Optional[str] = None) -> str:
        self._ensure_started()
        page = await self._context.new_page()
        self._tab_counter += 1
        tab_id = f"tab-{self._tab_counter}"
        state = TabState(page=page, tab_id=tab_id)
        self._tabs[tab_id] = state

        page.on("dialog", self._make_dialog_handler(tab_id))
        page.on("download", self._make_download_handler(tab_id))

        self._active_tab_id = tab_id
        if url:
            await page.goto(url, wait_until="domcontentloaded")
        logger.info("Opened tab %s%s", tab_id, f" -> {url}" if url else "")
        return tab_id

    async def close_tab(self, tab_id: Optional[str] = None) -> str:
        self._ensure_started()
        target_id = tab_id or self._active_tab_id
        state = self._get_tab(target_id)
        await state.page.close()
        del self._tabs[target_id]
        logger.info("Closed tab %s", target_id)

        if self._active_tab_id == target_id:
            self._active_tab_id = next(iter(self._tabs), None)
            if self._active_tab_id is None:
                await self.open_tab()
        return self._active_tab_id

    async def switch_tab(self, tab_id: str) -> str:
        self._ensure_started()
        state = self._get_tab(tab_id)
        await state.page.bring_to_front()
        self._active_tab_id = tab_id
        return tab_id

    def list_tabs(self) -> List[Dict[str, Any]]:
        self._ensure_started()
        return [
            {
                "tab_id": tid,
                "url": s.page.url,
                "title": None,
                "active": tid == self._active_tab_id,
            }
            for tid, s in self._tabs.items()
        ]

    def _get_tab(self, tab_id: Optional[str]) -> TabState:
        tab_id = tab_id or self._active_tab_id
        if tab_id is None or tab_id not in self._tabs:
            raise TabNotFoundError(f"Tab '{tab_id}' does not exist", tab_id=tab_id)
        return self._tabs[tab_id]

    def get_page(self, tab_id: Optional[str] = None) -> Page:
        self._ensure_started()
        return self._get_tab(tab_id).page

    @property
    def active_tab_id(self) -> Optional[str]:
        return self._active_tab_id

    def set_ref_map(self, tab_id: str, ref_map: Dict[str, str]) -> None:
        self._get_tab(tab_id).last_ref_map = ref_map

    def resolve_ref(self, tab_id: str, ref: str) -> Optional[str]:
        return self._get_tab(tab_id).last_ref_map.get(ref)

    def set_dialog_policy(
        self, tab_id: str, action: str, prompt_text: Optional[str] = None, persist: bool = True
    ) -> None:
        state = self._get_tab(tab_id)
        state.dialog_policy = DialogPolicy(action=action, prompt_text=prompt_text, persist=persist)

    def get_last_dialog(self, tab_id: str) -> Optional[DialogRecord]:
        return self._get_tab(tab_id).last_dialog

    def _make_dialog_handler(self, tab_id: str):
        async def handler(dialog: Dialog) -> None:
            state = self._tabs.get(tab_id)
            policy = state.dialog_policy if state else DialogPolicy()
            try:
                if policy.action == "accept":
                    await dialog.accept(policy.prompt_text or "")
                else:
                    await dialog.dismiss()
                taken = policy.action
            except Exception:
                logger.exception("Failed to handle dialog on %s", tab_id)
                taken = "error"

            record = DialogRecord(
                dialog_type=dialog.type,
                message=dialog.message,
                default_value=dialog.default_value,
                action_taken=taken,
                tab_id=tab_id,
            )
            if state:
                state.last_dialog = record
                if not policy.persist:
                    state.dialog_policy = DialogPolicy()
            logger.info(
                "Dialog on %s: type=%s message=%r -> %s",
                tab_id, dialog.type, dialog.message, taken,
            )

        return handler

    def _make_download_handler(self, tab_id: str):
        def handler(download: Download) -> None:
            asyncio.ensure_future(self._save_download(download, tab_id))

        return handler

    async def _save_download(self, download: Download, tab_id: str) -> None:
        suggested = download.suggested_filename or f"download-{uuid.uuid4().hex}"
        dest = os.path.join(self.downloads_dir, suggested)
        base, ext = os.path.splitext(dest)
        counter = 1
        while os.path.exists(dest):
            dest = f"{base}({counter}){ext}"
            counter += 1
        try:
            await download.save_as(dest)
            record = {
                "tab_id": tab_id,
                "suggested_filename": suggested,
                "saved_path": dest,
                "url": download.url,
            }
            self._downloads.append(record)
            logger.info("Download saved: %s -> %s", download.url, dest)
        except Exception:
            logger.exception("Failed to save download from %s", download.url)

    def get_downloads(self) -> List[Dict[str, Any]]:
        return list(self._downloads)

    async def wait_for_load(self, tab_id: Optional[str] = None, timeout_ms: Optional[int] = None) -> None:
        page = self.get_page(tab_id)
        try:
            await page.wait_for_load_state(
                "load", timeout=timeout_ms or self.default_timeout_ms
            )
        except PlaywrightTimeoutError as exc:
            raise BrowserTimeoutError(f"Timed out waiting for page load: {exc}") from exc
