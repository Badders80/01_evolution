"""
Webclaw Cloud Engine

High-quality web extraction with automatic anti-bot bypass.
Ported from Evolution_Content/scripts/scrape-webclaw.js

Config:
  WEBCLAW_API_KEY — from /home/evo/.env
  WEBCLAW_API_URL — default: https://api.webclaw.io/v1/extract
"""

import os
import time
from typing import Optional

import requests


# ── Config ──────────────────────────────────────────────────────
DEFAULT_API_URL = "https://api.webclaw.io/v1/extract"
MIN_CONTENT_LENGTH = 200  # Below this, consider the extraction empty
MAX_RETRIES = 3
RETRY_DELAY = 1.0


def _load_env():
    """Load WEBCLAW_API_KEY from /home/evo/.env if not in environment."""
    env_path = "/home/evo/.env"
    if not os.path.exists(env_path):
        return os.getenv("WEBCLAW_API_KEY", "")
    with open(env_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "WEBCLAW_API_KEY" in line:
                parts = line.split("=", 1)
                if len(parts) == 2:
                    return parts[1].strip().strip("\"'\"")
    return os.getenv("WEBCLAW_API_KEY", "")


class WebclawEngine:
    """Cloud scraper with anti-bot bypass. Primary engine for Cloudflare sites."""

    def __init__(self):
        self.api_key = _load_env()
        self.api_url = os.getenv("WEBCLAW_API_URL", DEFAULT_API_URL)
        self.session = requests.Session()

    def fetch(self, url: str, **kwargs) -> str:
        """
        Fetch raw HTML for a URL.

        Args:
            url: Target URL to scrape
            **kwargs: Passed through to Webclaw API (e.g. prompt for LLM extraction)

        Returns:
            Raw HTML string

        Raises:
            RuntimeError: If API key missing or all retries exhausted
        """
        if not self.api_key:
            raise RuntimeError("WEBCLAW_API_KEY not configured")

        payload = {"url": url, **kwargs}
        headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}

        last_err: Optional[Exception] = None
        for attempt in range(MAX_RETRIES):
            try:
                resp = self.session.post(
                    self.api_url,
                    json=payload,
                    headers=headers,
                    timeout=60,
                )
                resp.raise_for_status()
                data = resp.json()

                # Webclaw returns markdown or HTML depending on mode
                content = data.get("markdown", "") or data.get("html", "") or data.get("content", "")
                if len(content) < MIN_CONTENT_LENGTH:
                    raise RuntimeError(f"Empty-ish response ({len(content)} chars)")
                return content

            except Exception as e:
                last_err = e
                if attempt < MAX_RETRIES - 1:
                    time.sleep(RETRY_DELAY * (attempt + 1))

        raise RuntimeError(f"Webclaw failed after {MAX_RETRIES} attempts: {last_err}")

    def extract(self, url: str, prompt: str, **kwargs) -> dict:
        """
        LLM-guided extraction. Returns structured dict.

        Args:
            url: Target URL
            prompt: Natural language prompt telling the LLM what to extract
            **kwargs: Additional extraction parameters

        Returns:
            Parsed dict from the LLM response
        """
        if not self.api_key:
            raise RuntimeError("WEBCLAW_API_KEY not configured")

        payload = {"url": url, "prompt": prompt, "format": "json", **kwargs}
        headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}

        last_err: Optional[Exception] = None
        for attempt in range(MAX_RETRIES):
            try:
                resp = self.session.post(
                    self.api_url,
                    json=payload,
                    headers=headers,
                    timeout=120,
                )
                resp.raise_for_status()
                data = resp.json()

                # Webclaw returns extracted data in various shapes
                if "data" in data:
                    return data["data"]
                if "extracted" in data:
                    return data["extracted"]
                return data

            except Exception as e:
                last_err = e
                if attempt < MAX_RETRIES - 1:
                    time.sleep(RETRY_DELAY * (attempt + 1))

        raise RuntimeError(f"Webclaw extract failed after {MAX_RETRIES} attempts: {last_err}")