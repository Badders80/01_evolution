"""
HLT Mission Control — Horse lookup by microchip.

Attempts to resolve a NZ microchip number to horse data via loveracing.nz.
Since loveracing.nz does not expose a direct microchip→horse API, we:
1. Attempt a site search for the microchip number.
2. If that fails, return a clear error so the UI can prompt for manual entry.

Manual entry fields: name, sex, colour, sire_name, dam_name, foaling_date, breeder, trainer_id
"""

import re
from dataclasses import dataclass
from typing import Optional

import requests
from bs4 import BeautifulSoup

LOVERACING_SEARCH_URL = "https://www.loveracing.nz/search.aspx"
LOVERACING_HORSE_PROFILE_URL = "https://www.loveracing.nz/Horses/Trainers-and-Owners/horse-profile.aspx"


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
    source: str = "unknown"
    error: Optional[str] = None


def _extract_year_from_name(name: str) -> Optional[str]:
    """Try to pull a 4-digit year from the horse name, e.g. 'Prudentia (NZ) 2021'."""
    m = re.search(r"\b(19|20)\d{2}\b", name)
    return m.group(0) if m else None


def _month_number(month_str: str) -> int:
    """Convert abbreviated month to number."""
    months = {
        "jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6,
        "jul": 7, "aug": 8, "sep": 9, "oct": 10, "nov": 11, "dec": 12,
    }
    return months.get(month_str.lower().strip()[:3], 1)


def lookup_microchip(microchip: str, timeout: int = 15) -> HorseLookupResult:
    """
    Attempt to resolve a microchip via loveracing.nz search.
    Returns HorseLookupResult with either populated fields or an error.
    """
    result = HorseLookupResult(microchip=microchip)

    # Basic validation
    if not re.fullmatch(r"\d{15}", microchip):
        result.error = "Microchip must be exactly 15 digits."
        return result

    try:
        # Step 1: Search loveracing.nz for the microchip
        search_resp = requests.get(
            LOVERACING_SEARCH_URL,
            params={"search": microchip, "type": "horse"},
            timeout=timeout,
            headers={"User-Agent": "Mozilla/5.0 (EvolutionStables/1.0)"},
        )
        search_resp.raise_for_status()
    except Exception as exc:
        result.error = f"loveracing.nz search request failed: {exc}"
        return result

    soup = BeautifulSoup(search_resp.text, "html.parser")

    # Try to find a horse link in search results
    horse_link = None
    for a in soup.find_all("a", href=True):
        href = a["href"]
        if "horse-profile.aspx" in href.lower():
            horse_link = href
            break

    if not horse_link:
        result.error = "No horse profile found on loveracing.nz for this microchip."
        return result

    # Extract loveracing_id from query string
    m = re.search(r"[?&]horse_id=(\d+)", horse_link)
    if m:
        result.loveracing_id = int(m.group(1))
        result.breeding_url = f"{LOVERACING_HORSE_PROFILE_URL}?horse_id={result.loveracing_id}"

    # Step 2: Fetch profile page
    profile_url = horse_link if horse_link.startswith("http") else f"https://www.loveracing.nz{horse_link}"
    try:
        profile_resp = requests.get(
            profile_url,
            timeout=timeout,
            headers={"User-Agent": "Mozilla/5.0 (EvolutionStables/1.0)"},
        )
        profile_resp.raise_for_status()
    except Exception as exc:
        result.error = f"Profile page request failed: {exc}"
        return result

    psoup = BeautifulSoup(profile_resp.text, "html.parser")

    # Heuristic scraping — loveracing.nz uses tables and divs with labels
    text = psoup.get_text(separator="\n")
    lines = [line.strip() for line in text.splitlines() if line.strip()]

    def _find_after(label: str, fallback: Optional[str] = None) -> Optional[str]:
        for i, line in enumerate(lines):
            if label.lower() in line.lower():
                # Try next line first
                if i + 1 < len(lines):
                    return lines[i + 1]
                # Try same line after colon
                parts = line.split(":", 1)
                if len(parts) == 2:
                    return parts[1].strip()
        return fallback

    result.name = _find_after("Name", _find_after("Horse Name"))
    if result.name:
        year = _extract_year_from_name(result.name)
        if year and not result.foaling_date:
            result.foaling_date = f"{year}-01-01"

    sex = _find_after("Sex", _find_after("Gender"))
    if sex:
        result.sex = sex.lower().split()[0]

    colour = _find_after("Colour", _find_after("Color"))
    if colour:
        result.colour = colour.split()[0]

    sire = _find_after("Sire")
    if sire:
        result.sire_name = sire

    dam = _find_after("Dam")
    if dam:
        result.dam_name = dam

    breeder = _find_after("Breeder")
    if breeder:
        result.breeder = breeder

    trainer = _find_after("Trainer")
    if trainer:
        result.trainer_name = trainer

    # Try to find a more precise foaling date
    for line in lines:
        m = re.search(r"(\d{1,2})\s+([A-Za-z]{3,})\s+(\d{4})", line)
        if m:
            day, month_str, year = m.groups()
            try:
                month_num = _month_number(month_str)
                result.foaling_date = f"{year}-{month_num:02d}-{int(day):02d}"
                break
            except Exception:
                pass

    result.source = "loveracing.nz"
    return result
