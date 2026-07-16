"""
registry/builtin/web_tools.py
--------------------------------
Web access tools. Most require the `requests` package.

download_file writes to the local filesystem â€” same caution as the
write_* tools in file_tools.py applies (gate with caution in
production; it can be pointed at any URL, including ones serving
unexpected/large/malicious content).
"""

import os
import re
from pathlib import Path

from ..tools import Tool

_MAX_DOWNLOAD_BYTES = 20 * 1024 * 1024  # 20 MB cap


def _resolve_path(path: str) -> str:
    return str(Path(path).resolve())


def web_search(query: str) -> str:
    """Simple web search via the DuckDuckGo Instant Answer API (no API key needed)."""
    try:
        import requests

        resp = requests.get(
            "https://api.duckduckgo.com/",
            params={"q": query, "format": "json", "no_html": 1},
            timeout=10,
        )
        data = resp.json()
        abstract = data.get("AbstractText") or ""
        if abstract:
            return abstract
        topics = data.get("RelatedTopics", [])
        if topics and isinstance(topics[0], dict):
            return topics[0].get("Text", "No results found")
        return "No results found"
    except Exception as exc:
        return f"Search error: {exc}"


def fetch_url(url: str) -> str:
    """Fetches a URL and returns its raw content (truncated to 5000 chars)."""
    try:
        import requests

        resp = requests.get(url, timeout=10)
        text = resp.text
        return text[:5000] + ("... (truncated)" if len(text) > 5000 else "")
    except Exception as exc:
        return f"Fetch error: {exc}"


def browse_url(url: str) -> str:
    """Alias for fetch_url."""
    return fetch_url(url)


def scrape_webpage(url: str) -> str:
    """Fetches a URL and returns readable text with HTML tags stripped
    (unlike fetch_url, which returns raw HTML)."""
    try:
        import requests

        resp = requests.get(url, timeout=10)
        html = resp.text
        # Remove script/style blocks entirely, then strip remaining tags
        html = re.sub(r"<(script|style)[^>]*>.*?</\1>", " ", html, flags=re.DOTALL | re.IGNORECASE)
        text = re.sub(r"<[^>]+>", " ", html)
        text = re.sub(r"\s+", " ", text).strip()
        return text[:5000] + ("... (truncated)" if len(text) > 5000 else "")
    except Exception as exc:
        return f"Scrape error: {exc}"


def download_file(url: str, save_path: str) -> str:
    """Downloads a file from a URL to a local path (capped at 20MB)."""
    try:
        import requests

        resolved = _resolve_path(save_path)
        os.makedirs(os.path.dirname(resolved), exist_ok=True)
        with requests.get(url, timeout=15, stream=True) as resp:
            resp.raise_for_status()
            total = 0
            with open(resolved, "wb") as f:
                for chunk in resp.iter_content(chunk_size=8192):
                    total += len(chunk)
                    if total > _MAX_DOWNLOAD_BYTES:
                        f.close()
                        os.remove(resolved)
                        return f"Download error: file exceeds {_MAX_DOWNLOAD_BYTES // (1024*1024)}MB limit"
                    f.write(chunk)
        return f"Downloaded {total} bytes to {resolved}"
    except Exception as exc:
        return f"Download error: {exc}"


WEB_TOOLS = [
    Tool(name="web_search", description="Simple web search (DuckDuckGo)", func=web_search),
    Tool(name="fetch_url", description="Fetches raw content of a URL", func=fetch_url),
    Tool(name="browse_url", description="Alias for fetch_url", func=browse_url),
    Tool(name="scrape_webpage", description="Fetches a URL and extracts readable text (tags stripped)", func=scrape_webpage),
    Tool(name="download_file", description="Downloads a file from a URL to a local path (max 20MB)", func=download_file, requires_approval=True, read_only=False),
]
