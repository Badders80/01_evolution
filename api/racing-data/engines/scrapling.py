"""
Scrapling StealthyFetcher Engine

Local stealth fetcher for geo-blocked sites.
Ported from Evolution_Content/scripts/scrape-tab-nz.py

Usage:
  from engines.scrapling import ScraplingEngine
  html = ScraplingEngine().fetch(url)

Requires:
  scrapling package installed (see DNA/tech-radar/trials/T-2026-008-scrapling/)
"""

import os
import sys
from typing import Optional

# ── Scrapling path injection ────────────────────────────────────
# Try to find the trial venv site-packages
# The trial venv is at /home/evo/workspace/DNA/tech-radar/trials/T-2026-008-scrapling/venv
_SCRAPLING_VENV = "/home/evo/workspace/DNA/tech-radar/trials/T-2026-008-scrapling/venv"

for _sp in [
    os.path.join(_SCRAPLING_VENV, "lib", f"python{sys.version_info.major}.{sys.version_info.minor}", "site-packages"),
    os.path.join(os.path.dirname(sys.executable), "..", "lib", f"python{sys.version_info.major}.{sys.version_info.minor}", "site-packages"),
]:
    _sp_abs = os.path.abspath(_sp)
    if os.path.exists(_sp_abs) and _sp_abs not in sys.path:
        sys.path.insert(0, _sp_abs)

try:
    from scrapling.fetchers import StealthyFetcher
except ImportError:
    StealthyFetcher = None


class ScraplingEngine:
    """Local stealth fetcher. Zero API cost, good for geo-blocked sites."""

    def __init__(self):
        self._fetcher: Optional[StealthyFetcher] = None

    def _get_fetcher(self) -> StealthyFetcher:
        if self._fetcher is None:
            if StealthyFetcher is None:
                raise RuntimeError(
                    "Scrapling not installed. "
                    "Activate venv at workspace/DNA/tech-radar/trials/T-2026-008-scrapling/venv"
                )
            self._fetcher = StealthyFetcher()
        return self._fetcher

    def fetch(self, url: str, **kwargs) -> str:
        """
        Fetch raw HTML via StealthyFetcher.

        Args:
            url: Target URL
            **kwargs: Passed to fetcher (e.g. timeout, retries)

        Returns:
            Raw HTML string
        """
        fetcher = self._get_fetcher()
        page = fetcher.fetch(url, **kwargs)
        # Scrapling Response: .text returns text nodes only (0 for pure HTML).
        # .html_content returns the full HTML string.
        return page.html_content or ""
