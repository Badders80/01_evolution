"""
Racing Data — Engines

Generic scraping engines (Option B: copied per module).
These are source-agnostic HTTP fetchers that handle anti-bot measures.

Engines:
  WebclawEngine   — Cloud API with built-in Cloudflare bypass
  ScraplingEngine — Local stealth fetcher (zero API cost)
  PlaywrightEngine — Browser automation (heaviest, always works)

Usage:
  from engines import WebclawEngine
  html = await WebclawEngine().fetch(url)
"""

from . import webclaw, scrapling

__all__ = ["webclaw", "scrapling"]
