"""miStable email helpers — report URLs and embedded Vimeo resolution."""

from __future__ import annotations

import html as htmlmod
import logging
import re
from typing import Optional
from urllib.parse import urljoin

import requests

logger = logging.getLogger(__name__)

_REPORT_PATH_RE = re.compile(
    r"https?://mistable\.com/site/report/key/[a-f0-9]+/id/[a-f0-9]+",
    re.IGNORECASE,
)
_VIMEO_THUMB_RE = re.compile(
    r"https?://mistable\.com/site/vimeoThumb/id/(\d+)",
    re.IGNORECASE,
)
_VIMEO_PLAYER_RE = re.compile(
    r"https?://player\.vimeo\.com/video/(\d+)\?([^\"'\s<>]+)",
    re.IGNORECASE,
)


def extract_report_url(body: str) -> Optional[str]:
    if not body:
        return None
    decoded = htmlmod.unescape(body)
    match = _REPORT_PATH_RE.search(decoded)
    return match.group(0) if match else None


def extract_vimeo_id_from_email(body: str) -> Optional[str]:
    if not body:
        return None
    decoded = htmlmod.unescape(body)
    match = _VIMEO_THUMB_RE.search(decoded)
    return match.group(1) if match else None


def fetch_report_player_url(report_url: str, timeout: int = 30) -> Optional[str]:
    """Fetch a signed miStable report page and return the Vimeo player URL."""
    logger.info("Fetching miStable report page: %s", report_url[:80])
    resp = requests.get(
        report_url,
        timeout=timeout,
        headers={"User-Agent": "Mozilla/5.0 (compatible; EvolutionEmailIngest/1.0)"},
    )
    resp.raise_for_status()
    match = _VIMEO_PLAYER_RE.search(resp.text)
    if not match:
        return None
    video_id, query = match.group(1), match.group(2)
    return f"https://player.vimeo.com/video/{video_id}?{query}"


def resolve_mistable_video_url(body: str) -> Optional[str]:
    """Resolve the best downloadable media URL from a miStable email body."""
    report_url = extract_report_url(body)
    if report_url:
        try:
            player_url = fetch_report_player_url(report_url)
            if player_url:
                return player_url
        except Exception as exc:
            logger.warning("Failed to resolve Vimeo from miStable report: %s", exc)

    vimeo_id = extract_vimeo_id_from_email(body)
    if vimeo_id:
        return urljoin("https://player.vimeo.com/video/", vimeo_id)

    return None