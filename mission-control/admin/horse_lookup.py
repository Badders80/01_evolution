"""
Mission Control — Horse lookup by microchip or loveracing.nz URL.

Fetch order (Cloudflare-aware):
  1. curl_cffi TLS impersonation (bypasses CF on loveracing.nz)
  2. plain requests (legacy fallback)

Optional: set LOVERACING_USE_SCRAPERS=1 to also try _shared/scrapers
(Webclaw → Scrapling) between curl_cffi and requests.

Parse: local breeding-page structure (same fields as industry-data adapter).
Does NOT import 05_industry-data (avoids pulling Playwright/Scrapling on request path).
"""

from __future__ import annotations

import os
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Optional
from urllib.parse import urlencode

import requests
from bs4 import BeautifulSoup

LOVERACING_SEARCH_URL = "https://www.loveracing.nz/search.aspx"
LOVERACING_HORSE_PROFILE_URL = (
    "https://www.loveracing.nz/Horses/Trainers-and-Owners/horse-profile.aspx"
)

_TOOLS_DIR = Path(__file__).resolve().parents[1]
_MONOREPO = _TOOLS_DIR.parents[1]
_SHARED = _MONOREPO / "_shared"

_BROWSER_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "Accept-Language": "en-NZ,en;q=0.9",
    "DNT": "1",
    "Connection": "keep-alive",
}


@dataclass
class HorseLookupResult:
    microchip: str
    name: Optional[str] = None
    sex: Optional[str] = None
    colour: Optional[str] = None
    sire_name: Optional[str] = None
    dam_name: Optional[str] = None
    foaling_date: Optional[str] = None
    breeder: Optional[str] = None
    trainer_name: Optional[str] = None
    loveracing_id: Optional[int] = None
    breeding_url: Optional[str] = None
    life_number: Optional[str] = None
    source: str = "unknown"
    error: Optional[str] = None


# ── fetch ─────────────────────────────────────────────────────────────────────

def _is_challenge_html(html: str) -> bool:
    head = (html or "")[:2500].lower()
    if "just a moment" in head:
        return True
    if "cf-browser-verification" in head or "cf-challenge" in head:
        return True
    if "attention required" in head and "cloudflare" in head:
        return True
    return False


def _fetch_curl_cffi(url: str, *, params: Optional[dict] = None, timeout: int = 30) -> str:
    from curl_cffi import requests as cffi_requests

    last_err: Optional[Exception] = None
    for impersonate in ("chrome", "chrome124", "chrome120"):
        try:
            resp = cffi_requests.get(
                url,
                params=params,
                impersonate=impersonate,
                timeout=timeout,
                headers=_BROWSER_HEADERS,
                allow_redirects=True,
            )
            body = resp.text or ""
            if resp.status_code == 403 and "cloudflare" in body.lower():
                last_err = RuntimeError(f"curl_cffi {impersonate}: Cloudflare 403")
                continue
            if resp.status_code >= 400:
                last_err = RuntimeError(f"curl_cffi {impersonate}: HTTP {resp.status_code}")
                continue
            if _is_challenge_html(body):
                last_err = RuntimeError(f"curl_cffi {impersonate}: CF challenge page")
                continue
            if len(body) < 200:
                last_err = RuntimeError(f"curl_cffi {impersonate}: empty body")
                continue
            return body
        except Exception as exc:
            last_err = exc
    raise RuntimeError(f"curl_cffi failed: {last_err}")


def _fetch_shared_scrapers(url: str) -> str:
    """Optional path — only if LOVERACING_USE_SCRAPERS=1."""
    if str(_SHARED) not in sys.path:
        sys.path.insert(0, str(_SHARED))
    from scrapers import WebclawEngine, ScraplingEngine  # type: ignore

    errors: list[str] = []
    for EngineClass in (WebclawEngine, ScraplingEngine):
        try:
            engine = EngineClass()
            if hasattr(engine, "available") and not engine.available:
                continue
            html = engine.fetch(url)
            if html and not _is_challenge_html(html) and len(html) >= 200:
                return html
            errors.append(f"{EngineClass.__name__}: empty/challenge")
        except Exception as exc:
            errors.append(f"{EngineClass.__name__}: {exc}")
    raise RuntimeError("; ".join(errors) or "shared scrapers unavailable")


def _fetch_requests(url: str, *, params: Optional[dict] = None, timeout: int = 30) -> str:
    resp = requests.get(url, params=params, timeout=timeout, headers=_BROWSER_HEADERS)
    resp.raise_for_status()
    html = resp.text or ""
    if _is_challenge_html(html) or (
        resp.status_code == 403 and "cloudflare" in html.lower()
    ):
        raise RuntimeError("requests: Cloudflare blocked")
    return html


def _http_get(url: str, *, params: Optional[dict] = None, timeout: int = 30) -> str:
    """Cloudflare-aware GET. Prefer curl_cffi."""
    full_url = url
    if params:
        qs = urlencode(params)
        full_url = f"{url}?{qs}" if "?" not in url else f"{url}&{qs}"

    errors: list[str] = []

    try:
        return _fetch_curl_cffi(url, params=params, timeout=timeout)
    except Exception as exc:
        errors.append(f"curl_cffi: {exc}")

    if os.environ.get("LOVERACING_USE_SCRAPERS", "").strip() in ("1", "true", "yes"):
        try:
            return _fetch_shared_scrapers(full_url)
        except Exception as exc:
            errors.append(f"scrapers: {exc}")

    try:
        return _fetch_requests(url, params=params, timeout=timeout)
    except Exception as exc:
        errors.append(f"requests: {exc}")

    raise RuntimeError(" | ".join(errors))


def _cloudflare_or_http_error(exc: Exception) -> str:
    msg = str(exc).lower()
    if "cloudflare" in msg or "cf challenge" in msg or "403" in msg:
        return "External lookup blocked by Cloudflare. Enter details manually below."
    if isinstance(exc, requests.exceptions.HTTPError) and exc.response is not None:
        return f"External lookup failed ({exc.response.status_code}). Enter details manually below."
    return f"External lookup failed: {exc}. Enter details manually below."


# ── parse ─────────────────────────────────────────────────────────────────────

def _extract_year_from_name(name: str) -> Optional[str]:
    m = re.search(r"\b(19|20)\d{2}\b", name)
    return m.group(0) if m else None


def _month_number(month_str: str) -> int:
    months = {
        "jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6,
        "jul": 7, "aug": 8, "sep": 9, "oct": 10, "nov": 11, "dec": 12,
    }
    return months.get(month_str.lower().strip()[:3], 1)


def _normalize_date(value) -> Optional[str]:
    if value is None:
        return None
    if hasattr(value, "isoformat"):
        return value.isoformat()
    s = str(value).strip()
    if not s:
        return None
    m = re.fullmatch(r"(\d{1,2})/(\d{1,2})/(\d{4})", s)
    if m:
        d, mo, y = m.groups()
        return f"{y}-{int(mo):02d}-{int(d):02d}"
    return s


def _parse_colour_sex(text: str) -> tuple[Optional[str], Optional[str]]:
    if not text:
        return None, None
    colours = ["Bay", "Chestnut", "Brown", "Grey", "Black", "Roan"]
    sexes = {
        "colt": ["colt"],
        "filly": ["filly"],
        "gelding": ["gelding"],
        "mare": ["mare"],
        "stallion": ["stallion"],
        "horse": ["horse"],
    }
    found_colour, found_sex = None, None
    for word in text.split():
        w = word.strip().rstrip(".")
        for c in colours:
            if w.lower() == c.lower():
                found_colour = c
                break
        for sex_key, variants in sexes.items():
            if w.lower() in variants:
                found_sex = sex_key
                break
    return found_colour, found_sex


def _parse_breeding_dom(html: str, result: HorseLookupResult) -> bool:
    """
    Structured parse of loveracing breeding pages (h2.horse-name, ul.horse-attr, strong labels).
    Mirrors 05_industry-data adapters.loveracing.parse_breeding_page without importing it.
    """
    soup = BeautifulSoup(html, "html.parser")
    got = False

    name_tag = soup.find("h2", class_="horse-name") or soup.find("h2")
    if name_tag:
        name = name_tag.get_text(strip=True)
        if name and "loveracing" not in name.lower():
            result.name = name
            got = True

    if not result.name and soup.title and soup.title.string:
        title = soup.title.string.split("/")[0].strip()
        if title and "loveracing" not in title.lower() and "search" not in title.lower():
            result.name = title
            got = True

    attr_list = soup.find("ul", class_="horse-attr")
    colour_sex_blob = ""
    if attr_list:
        for li in attr_list.find_all("li", recursive=False):
            text = li.get_text(" ", strip=True)
            if text.startswith("Born:"):
                result.foaling_date = _normalize_date(text.replace("Born:", "").strip())
                got = True
            elif "Sire:" in text:
                a = li.find("a")
                result.sire_name = a.get_text(strip=True) if a else text.replace("Sire:", "").strip()
                got = True
            elif "Dam:" in text:
                a = li.find("a")
                result.dam_name = a.get_text(strip=True) if a else text.replace("Dam:", "").strip()
                got = True
            elif not text.startswith("Age:"):
                colour_sex_blob = text

    colour, sex = _parse_colour_sex(colour_sex_blob)
    if colour:
        result.colour = colour
        got = True
    if sex:
        result.sex = sex
        got = True

    # strong-label detail grid (Microchip, Life no, Breeder, …)
    for strong in soup.find_all("strong"):
        label = strong.get_text(strip=True).rstrip(":")
        value = ""
        for sibling in strong.next_siblings:
            if isinstance(sibling, str):
                value += sibling
            elif getattr(sibling, "name", None) in (None, "br"):
                continue
            else:
                # stop at next element that's not pure whitespace text
                break
        value = value.strip()
        if not value:
            # value often on next text node after a br, or next sibling tag text
            parent = strong.parent
            if parent:
                full = parent.get_text(" ", strip=True)
                if full.lower().startswith(label.lower()):
                    value = full[len(label):].lstrip(": ").strip()

        if not value:
            continue
        key = label.lower()
        if key == "microchip":
            digits = re.sub(r"\D", "", value)
            if re.fullmatch(r"\d{15}", digits):
                result.microchip = digits
                got = True
        elif key in ("life no", "life number"):
            result.life_number = value
            got = True
        elif key == "breeder":
            result.breeder = value
            got = True
        elif key == "trainer":
            result.trainer_name = value
            got = True
        elif key in ("foaling date", "born"):
            result.foaling_date = _normalize_date(value)
            got = True
        elif key == "sire" and not result.sire_name:
            result.sire_name = value
            got = True
        elif key == "dam" and not result.dam_name:
            result.dam_name = value
            got = True
        elif key == "sex" and not result.sex:
            result.sex = value.lower().split()[0]
            got = True
        elif key in ("colour", "color") and not result.colour:
            result.colour = value.split()[0]
            got = True

    return got


def _parse_profile_html(html: str, result: HorseLookupResult) -> HorseLookupResult:
    """Parse loveracing profile / breeding HTML into result fields."""
    if _parse_breeding_dom(html, result):
        result.source = "loveracing.nz"
        # Fill gaps from line scan below if needed
        if result.name and result.microchip and result.sire_name:
            return result

    psoup = BeautifulSoup(html, "html.parser")
    text = psoup.get_text(separator="\n")
    lines = [line.strip() for line in text.splitlines() if line.strip()]

    def _find_label(label: str) -> Optional[str]:
        want = label.lower().rstrip(":")
        for i, line in enumerate(lines):
            low = line.lower().strip()
            if low == f"{want}:" or low.startswith(f"{want}:"):
                after = line.split(":", 1)[1].strip() if ":" in line else ""
                if after:
                    return after
                if i + 1 < len(lines):
                    return lines[i + 1]
        return None

    if not result.name and psoup.title and psoup.title.string:
        title = psoup.title.string.split("/")[0].strip()
        if title and "loveracing" not in title.lower() and "search" not in title.lower():
            result.name = title

    if not result.name:
        h2 = psoup.find("h2")
        if h2:
            result.name = h2.get_text(strip=True)

    if result.name and not result.foaling_date:
        year = _extract_year_from_name(result.name)
        if year:
            result.foaling_date = f"{year}-01-01"

    if not result.sex:
        sex = _find_label("Sex") or _find_label("Gender")
        if sex:
            result.sex = sex.lower().split()[0]

    if not result.colour:
        colour = _find_label("Colour") or _find_label("Color")
        if colour:
            result.colour = colour.split()[0]

    if not result.microchip:
        chip = _find_label("Microchip") or _find_label("Microchip Number")
        if chip:
            digits = re.sub(r"\D", "", chip)
            if re.fullmatch(r"\d{15}", digits):
                result.microchip = digits
        else:
            m = re.search(r"\b(985\d{12})\b", html)
            if m:
                result.microchip = m.group(1)

    if not result.life_number:
        life = _find_label("Life no") or _find_label("Life number")
        if life:
            result.life_number = life

    if not result.sire_name:
        sire = _find_label("Sire")
        if sire:
            result.sire_name = sire

    if not result.dam_name:
        dam = _find_label("Dam")
        if dam:
            result.dam_name = dam

    if not result.breeder:
        breeder = _find_label("Breeder")
        if breeder:
            result.breeder = breeder

    if not result.trainer_name:
        trainer = _find_label("Trainer")
        if trainer and "profile search" not in trainer.lower():
            result.trainer_name = trainer

    if not result.foaling_date:
        foaled = _find_label("Foaling date") or _find_label("Born")
        if foaled:
            result.foaling_date = _normalize_date(foaled)
        else:
            for line in lines:
                m = re.search(r"(\d{1,2})\s+([A-Za-z]{3,})\s+(\d{4})", line)
                if m:
                    day, month_str, year = m.groups()
                    try:
                        result.foaling_date = (
                            f"{year}-{_month_number(month_str):02d}-{int(day):02d}"
                        )
                        break
                    except Exception:
                        pass

    result.source = "loveracing.nz"
    return result


def _fetch_profile(url: str, result: HorseLookupResult, timeout: int = 30) -> HorseLookupResult:
    try:
        html = _http_get(url, timeout=timeout)
    except Exception as exc:
        result.error = _cloudflare_or_http_error(exc)
        return result
    return _parse_profile_html(html, result)


def _ids_from_url(url: str) -> tuple[Optional[int], Optional[str]]:
    """Extract loveracing horse id and a canonical breeding/profile url if possible."""
    m = re.search(r"/Breeding/(\d+)/", url, re.I)
    if m:
        hid = int(m.group(1))
        full = url if url.startswith("http") else f"https://www.loveracing.nz{url}"
        full = full.replace("://loveracing.nz", "://www.loveracing.nz")
        return hid, full

    m = re.search(r"[?&]horse_id=(\d+)", url, re.I)
    if m:
        hid = int(m.group(1))
        return hid, f"{LOVERACING_HORSE_PROFILE_URL}?horse_id={hid}"

    m = re.search(r"/Horses/[^?]+\?horse_id=(\d+)", url, re.I)
    if m:
        hid = int(m.group(1))
        return hid, f"{LOVERACING_HORSE_PROFILE_URL}?horse_id={hid}"
    return None, None


def lookup_url(url: str, timeout: int = 30) -> HorseLookupResult:
    """Resolve a loveracing.nz breeding or profile URL."""
    result = HorseLookupResult(microchip="")
    url = url.strip()
    if not url.startswith("http"):
        url = "https://" + url.lstrip("/")

    hid, canonical = _ids_from_url(url)
    if hid:
        result.loveracing_id = hid
        result.breeding_url = canonical or url
        return _fetch_profile(canonical or url, result, timeout=timeout)

    result.breeding_url = url
    return _fetch_profile(url, result, timeout=timeout)


def lookup_microchip(microchip: str, timeout: int = 30) -> HorseLookupResult:
    """
    Attempt to resolve a microchip via loveracing.nz search.
    Returns HorseLookupResult with either populated fields or an error.
    """
    result = HorseLookupResult(microchip=microchip)

    if not re.fullmatch(r"\d{15}", microchip):
        result.error = "Microchip must be exactly 15 digits."
        return result

    try:
        html = _http_get(
            LOVERACING_SEARCH_URL,
            params={"search": microchip, "type": "horse"},
            timeout=timeout,
        )
    except Exception as exc:
        result.error = _cloudflare_or_http_error(exc)
        return result

    soup = BeautifulSoup(html, "html.parser")

    horse_link = None
    for a in soup.find_all("a", href=True):
        href = a["href"]
        if "horse-profile.aspx" in href.lower() or "/Breeding/" in href:
            horse_link = href
            break

    if not horse_link:
        result.error = (
            "No horse profile found on loveracing.nz for this microchip. "
            "Paste a breeding URL instead, or enter details manually."
        )
        return result

    m = re.search(r"[?&]horse_id=(\d+)", horse_link)
    if not m:
        m = re.search(r"/Breeding/(\d+)/", horse_link)
    if m:
        result.loveracing_id = int(m.group(1))
        if "/Breeding/" in horse_link:
            result.breeding_url = (
                horse_link
                if horse_link.startswith("http")
                else f"https://www.loveracing.nz{horse_link}"
            )
        else:
            result.breeding_url = (
                f"{LOVERACING_HORSE_PROFILE_URL}?horse_id={result.loveracing_id}"
            )

    profile_url = (
        horse_link if horse_link.startswith("http") else f"https://www.loveracing.nz{horse_link}"
    )
    return _fetch_profile(profile_url, result, timeout=timeout)


def lookup_horse(query: str, timeout: int = 30) -> HorseLookupResult:
    """
    Resolve either a 15-digit microchip OR a loveracing.nz URL.
    Same confirm-step fields either way; Cloudflare/errors fall through to manual entry.
    """
    q = (query or "").strip()
    if not q:
        r = HorseLookupResult(microchip="")
        r.error = "Enter a 15-digit microchip or a loveracing.nz URL."
        return r

    if re.fullmatch(r"\d{15}", q):
        return lookup_microchip(q, timeout=timeout)

    if (
        "loveracing" in q.lower()
        or q.startswith("http")
        or "/Breeding/" in q
        or "horse_id=" in q.lower()
    ):
        return lookup_url(q, timeout=timeout)

    if q.isdigit():
        r = HorseLookupResult(microchip=q)
        r.error = "Microchip must be exactly 15 digits (or paste a loveracing.nz URL)."
        return r

    r = HorseLookupResult(microchip="")
    r.error = "Paste a 15-digit microchip or a loveracing.nz profile/breeding URL."
    return r
