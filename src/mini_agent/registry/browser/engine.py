from __future__ import annotations

import os
import sys
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from .exceptions import (
    BrowserNotStartedError,
    BrowserTimeoutError,
    TabNotFoundError,
)

from .logger import get_logger

logger = get_logger(__name__)

DEFAULT_VIEWPORT = {"width": 1366, "height": 768}
DEFAULT_TIMEOUT_MS = 30_000

UC_OPTIONS = [
    "--no-sandbox",
    "--disable-setuid-sandbox",
    "--disable-dev-shm-usage",
    "--disable-gpu",
    "--disable-extensions",
    "--disable-background-networking",
    "--disable-blink-features=AutomationControlled",
]

INIT_SCRIPT = """
Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
Object.defineProperty(navigator, 'plugins', { get: () => [1, 2, 3, 4, 5] });
Object.defineProperty(navigator, 'languages', { get: () => ['en-US', 'en'] });
window.chrome = { runtime: {} };
const originalQuery = window.navigator.permissions.query;
window.navigator.permissions.query = (params) => (
    params.name === 'notifications'
        ? Promise.resolve({ state: 'denied' })
        : originalQuery(params)
);
"""


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
    handle: str
    tab_id: str
    dialog_policy: DialogPolicy = field(default_factory=DialogPolicy)
    last_dialog: Optional[DialogRecord] = None
    last_ref_map: Dict[str, str] = field(default_factory=dict)


class BrowserManager:
    def __init__(
        self,
        headless: bool = True,
        downloads_dir: str = "./downloads",
        screenshots_dir: str = "./screenshots",
        viewport: Optional[Dict[str, int]] = None,
        user_agent: Optional[str] = None,
        default_timeout_ms: int = DEFAULT_TIMEOUT_MS,
        extra_launch_args: Optional[List[str]] = None,
        proxy: Optional[Dict[str, str]] = None,
        version_main: Optional[int] = None,
    ):
        self.headless = headless
        self.downloads_dir = os.path.abspath(downloads_dir)
        self.screenshots_dir = os.path.abspath(screenshots_dir)
        self.viewport = viewport or DEFAULT_VIEWPORT
        self.user_agent = user_agent
        self.default_timeout_ms = default_timeout_ms
        self.launch_args = extra_launch_args or UC_OPTIONS
        self.proxy = proxy
        self.version_main = version_main or self._detect_chrome_version()

        self._driver: Optional[uc.Chrome] = None
        self._tabs: Dict[str, TabState] = {}
        self._active_tab_id: Optional[str] = None
        self._tab_counter = 0
        self._downloads: List[Dict[str, Any]] = []

    @staticmethod
    def _detect_chrome_version() -> int:
        try:
            import winreg
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Google\Chrome\BLBeacon")
            version = winreg.QueryValueEx(key, "version")[0]
            return int(version.split(".")[0])
        except Exception:
            pass
        try:
            import subprocess
            result = subprocess.run(
                [r"C:\Program Files\Google\Chrome\Application\chrome.exe", "--version"],
                capture_output=True, text=True, timeout=5,
            )
            if result.returncode == 0:
                part = result.stdout.strip().split()[-1]
                return int(part.split(".")[0])
        except Exception:
            pass
        return 0

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def start(self) -> None:
        if self._driver is not None:
            return

        os.makedirs(self.downloads_dir, exist_ok=True)
        os.makedirs(self.screenshots_dir, exist_ok=True)

        options = uc.ChromeOptions()
        for arg in self.launch_args:
            options.add_argument(arg)

        options.add_argument(f"--window-size={self.viewport['width']},{self.viewport['height']}")

        prefs = {
            "download.default_directory": self.downloads_dir,
            "download.prompt_for_download": False,
            "download.directory_upgrade": True,
            "safebrowsing.enabled": True,
        }
        options.add_experimental_option("prefs", prefs)

        if self.user_agent:
            options.add_argument(f"--user-agent={self.user_agent}")

        if self.proxy:
            proxy_str = self.proxy.get("server", "")
            if proxy_str:
                options.add_argument(f"--proxy-server={proxy_str}")

        self._driver = uc.Chrome(options=options, version_main=self.version_main)

        self._driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
            "source": INIT_SCRIPT,
        })

        self.open_tab()

        logger.info(
            "Browser started (engine=undetected-chromedriver, headless=%s, viewport=%s)",
            self.headless,
            self.viewport,
        )

    def shutdown(self) -> None:
        try:
            if self._driver is not None:
                self._driver.quit()
        except Exception:
            logger.exception("Error shutting down browser")

        self._driver = None
        self._tabs.clear()
        self._active_tab_id = None
        logger.info("Browser shut down")

    def _ensure_started(self) -> None:
        if self._driver is None:
            raise BrowserNotStartedError(
                "Browser has not been started. Call agent.start() first."
            )

    # ------------------------------------------------------------------
    # Tab management
    # ------------------------------------------------------------------

    def open_tab(self, url: Optional[str] = None) -> str:
        self._ensure_started()

        if self._active_tab_id is not None:
            self._driver.execute_script("window.open('');")
            handles = self._driver.window_handles
            handle = handles[-1]
            self._driver.switch_to.window(handle)
        else:
            handle = self._driver.current_window_handle

        self._tab_counter += 1
        tab_id = f"tab-{self._tab_counter}"
        state = TabState(handle=handle, tab_id=tab_id)
        self._tabs[tab_id] = state
        self._active_tab_id = tab_id

        if url:
            self._driver.get(url)

        logger.info("Opened tab %s%s", tab_id, f" -> {url}" if url else "")
        return tab_id

    def close_tab(self, tab_id: Optional[str] = None) -> str:
        self._ensure_started()
        target_id = tab_id or self._active_tab_id
        state = self._get_tab(target_id)

        self._driver.switch_to.window(state.handle)
        self._driver.execute_script("window.close();")

        del self._tabs[target_id]
        logger.info("Closed tab %s", target_id)

        if self._active_tab_id == target_id:
            remaining_handles = self._driver.window_handles
            if remaining_handles:
                first = remaining_handles[0]
                self._driver.switch_to.window(first)
                self._active_tab_id = next(
                    (tid for tid, s in self._tabs.items() if s.handle == first),
                    None
                )
                if self._active_tab_id is None:
                    self._active_tab_id = next(iter(self._tabs), None)
            else:
                self._active_tab_id = None
                self.open_tab()

        return self._active_tab_id

    def switch_tab(self, tab_id: str) -> str:
        self._ensure_started()
        self._switch_to_tab(tab_id)
        self._active_tab_id = tab_id
        return tab_id

    def _switch_to_tab(self, tab_id: str) -> None:
        state = self._get_tab(tab_id)
        self._driver.switch_to.window(state.handle)

    def list_tabs(self) -> List[Dict[str, Any]]:
        self._ensure_started()
        current = self._driver.current_window_handle
        try:
            all_handles = self._driver.window_handles
        except Exception:
            all_handles = [s.handle for s in self._tabs.values()]

        results = []
        for tid, s in self._tabs.items():
            url = None
            title = None
            try:
                if s.handle in all_handles:
                    self._driver.switch_to.window(s.handle)
                    url = self._driver.current_url
                    title = self._driver.title
            except Exception:
                pass
            results.append({
                "tab_id": tid,
                "url": url,
                "title": title,
                "active": tid == self._active_tab_id,
            })
        try:
            self._driver.switch_to.window(current)
        except Exception:
            pass
        return results

    # ------------------------------------------------------------------
    # Tab helpers
    # ------------------------------------------------------------------

    def _get_tab(self, tab_id: Optional[str]) -> TabState:
        tab_id = tab_id or self._active_tab_id
        if tab_id is None or tab_id not in self._tabs:
            raise TabNotFoundError(f"Tab '{tab_id}' does not exist", tab_id=tab_id)
        return self._tabs[tab_id]

    def get_page(self, tab_id: Optional[str] = None) -> Any:
        self._ensure_started()
        state = self._get_tab(tab_id)
        self._driver.switch_to.window(state.handle)
        return self._driver

    @property
    def active_tab_id(self) -> Optional[str]:
        return self._active_tab_id

    # ------------------------------------------------------------------
    # Ref map (observe → click/fill routing)
    # ------------------------------------------------------------------

    def set_ref_map(self, tab_id: str, ref_map: Dict[str, str]) -> None:
        self._get_tab(tab_id).last_ref_map = ref_map

    def resolve_ref(self, tab_id: str, ref: str) -> Optional[str]:
        return self._get_tab(tab_id).last_ref_map.get(ref)

    # ------------------------------------------------------------------
    # Dialog handling
    # ------------------------------------------------------------------

    def set_dialog_policy(
        self, tab_id: str, action: str, prompt_text: Optional[str] = None, persist: bool = True
    ) -> None:
        state = self._get_tab(tab_id)
        state.dialog_policy = DialogPolicy(action=action, prompt_text=prompt_text, persist=persist)

    def get_last_dialog(self, tab_id: str) -> Optional[DialogRecord]:
        return self._get_tab(tab_id).last_dialog

    def handle_dialog(self, tab_id: str) -> None:
        state = self._get_tab(tab_id)
        try:
            alert = self._driver.switch_to.alert
            record = DialogRecord(
                dialog_type=alert.text,
                message=alert.text,
                default_value=None,
                action_taken=state.dialog_policy.action,
                tab_id=tab_id,
            )
            if state.dialog_policy.action == "accept":
                alert.accept()
            else:
                alert.dismiss()
            state.last_dialog = record
            if not state.dialog_policy.persist:
                state.dialog_policy = DialogPolicy()
        except Exception:
            pass

    # ------------------------------------------------------------------
    # Downloads
    # ------------------------------------------------------------------

    def get_downloads(self) -> List[Dict[str, Any]]:
        return list(self._downloads)

    # ------------------------------------------------------------------
    # Waits
    # ------------------------------------------------------------------

    def wait_for_load(self, tab_id: Optional[str] = None, timeout_ms: Optional[int] = None) -> None:
        driver = self.get_page(tab_id)
        timeout = (timeout_ms or self.default_timeout_ms) / 1000.0
        try:
            WebDriverWait(driver, timeout).until(
                lambda d: d.execute_script("return document.readyState") == "complete"
            )
        except Exception as exc:
            raise BrowserTimeoutError(f"Timed out waiting for page load: {exc}") from exc
