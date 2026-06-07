"""
loveracing.nz Adapter

Parses raw HTML from loveracing.nz into structured RaceResult records.
Uses BeautifulSoup for robust DOM parsing.

Pages handled:
  - Breeding page: https://loveracing.nz/Breeding/{id}/{slug}.aspx
  - Race history: extracted from horse profile or entry detail modals

Output:
  - LoveracingRef: static horse identity
  - List[RaceResult]: one per race start
"""

import re
from datetime import date
from typing import List, Optional

from bs4 import BeautifulSoup

from engines.webclaw import WebclawEngine
from engines.scrapling import ScraplingEngine


# ── URL builders ────────────────────────────────────────────────
def breeding_url(loveracing_id: int, name_slug: str) -> str:
    """Stud Book / Breeding page — static identity data."""
    return f"https://loveracing.nz/Breeding/{loveracing_id}/{name_slug}.aspx"


def race_history_url(loveracing_id: int) -> str:
    """
    Race history / performance page.
    Key: DisplayContext=Modal01 gives race history.
    DisplayContext=Modal (without 01) gives breeding page.
    """
    return f"https://loveracing.nz/Common/SystemTemplates/Modal/EntryDetail.aspx?HorseID={loveracing_id}&DisplayContext=Modal01"


def entry_detail_url(loveracing_id: int, **params) -> str:
    """Build EntryDetail.aspx URL for a specific race entry."""
    base = f"https://loveracing.nz/Common/SystemTemplates/Modal/EntryDetail.aspx?HorseID={loveracing_id}"
    for k, v in params.items():
        base += f"&{k}={v}"
    return base


# ── Fallback chain ──────────────────────────────────────────────
def fetch_html(url: str) -> str:
    """
    Try engines in order: Webclaw → Scrapling → raise.
    Returns raw HTML string.
    """
    errors: List[str] = []

    # 1. Webclaw Cloud
    try:
        engine = WebclawEngine()
        return engine.fetch(url)
    except Exception as e:
        errors.append(f"Webclaw: {e}")

    # 2. Scrapling StealthyFetcher
    try:
        engine = ScraplingEngine()
        return engine.fetch(url)
    except Exception as e:
        errors.append(f"Scrapling: {e}")

    raise RuntimeError(f"All engines failed for {url}: {'; '.join(errors)}")


# ── Parsing ─────────────────────────────────────────────────────
def parse_breeding_page(html: str, loveracing_id: int) -> dict:
    """
    Extract static horse identity from the breeding page HTML.
    Returns a dict matching LoveracingRef fields.
    """
    soup = BeautifulSoup(html, "lxml")

    # Name: <h2 class="horse-name">Prudentia (NZ) 2021</h2>
    name_tag = soup.find("h2", class_="horse-name")
    name = name_tag.get_text(strip=True) if name_tag else None

    # Attributes: <ul class="no-bullets horse-attr">
    attr_list = soup.find("ul", class_="horse-attr")
    attrs = {}
    if attr_list:
        for li in attr_list.find_all("li", recursive=False):
            text = li.get_text(" ", strip=True)
            if text.startswith("Born:"):
                attrs["born"] = text.replace("Born:", "").strip()
            elif text.startswith("Age:"):
                attrs["age"] = text.replace("Age:", "").strip()
            elif "Sire:" in text:
                # Extract text from <a> tag if present
                a = li.find("a")
                attrs["sire"] = a.get_text(strip=True) if a else text.replace("Sire:", "").strip()
            elif "Dam:" in text:
                a = li.find("a")
                attrs["dam"] = a.get_text(strip=True) if a else text.replace("Dam:", "").strip()
            else:
                # Could be "Bay Mare" (colour + sex combined)
                attrs["colour_sex"] = text

    # Detail grid: <strong>Microchip:</strong> 985125000126462
    detail_grid = soup.find("div", class_="content-block")
    if detail_grid:
        for strong in detail_grid.find_all("strong"):
            label = strong.get_text(strip=True).rstrip(":")
            # The value is in the next sibling text node
            value = ""
            for sibling in strong.next_siblings:
                if isinstance(sibling, str):
                    value += sibling
                else:
                    break
            value = value.strip()
            if label == "Microchip":
                attrs["microchip"] = value
            elif label == "Life no":
                attrs["life_number"] = value
            elif label == "Left shoulder":
                attrs["left_shoulder"] = value
            elif label == "Right shoulder":
                attrs["right_shoulder"] = value
            elif label == "Breeder":
                attrs["breeder"] = value
            elif label == "Trainer":
                attrs["trainer"] = value
            elif label == "PV":
                attrs["pv"] = value
            elif label == "BT":
                attrs["bt"] = value

    # Parse colour + sex
    colour, sex = _parse_colour_sex(attrs.get("colour_sex", ""))

    # Parse foaling date
    foaling_date = _parse_nz_date(attrs.get("born", ""))

    return {
        "loveracing_id": loveracing_id,
        "name": name,
        "name_slug": _name_to_slug(name),
        "microchip": attrs.get("microchip"),
        "life_number": attrs.get("life_number"),
        "foaling_date": foaling_date,
        "sex": sex,
        "colour": colour,
        "sire_name": attrs.get("sire"),
        "dam_name": attrs.get("dam"),
        "pv": attrs.get("pv", "").upper() == "Y",
        "bt": attrs.get("bt", "").upper() == "Y",
        "breeder": attrs.get("breeder"),
        "left_shoulder_brand": attrs.get("left_shoulder"),
        "right_shoulder_brand": attrs.get("right_shoulder"),
        "trainer": attrs.get("trainer"),  # Current trainer (from breeding page)
    }


def parse_race_history(html: str, horse_microchip: str, loveracing_id: int) -> List[dict]:
    """
    Extract race-by-race results from the horse's race history HTML.
    Source: EntryDetail.aspx?HorseID={id}&DisplayContext=Modal01
    Returns list of RaceResult dicts.
    """
    soup = BeautifulSoup(html, "lxml")
    results: List[dict] = []

    # Each race is a <table class="table-indepth">
    for table in soup.find_all("table", class_="table-indepth"):
        rows = table.find_all("tr")
        if len(rows) < 2:
            continue

        # Row 0: finish position, date, distance, race name, video, prize pool
        first_row = rows[0]
        cells = first_row.find_all(["td", "th"])
        if len(cells) < 6:
            continue

        placing_text = cells[0].get_text(strip=True)  # e.g. "5-13"
        date_text = cells[1].get_text(strip=True)       # e.g. "30 May 26"
        distance_text = cells[2].get_text(strip=True)  # e.g. "1200m"
        race_name = cells[3].get_text(strip=True)       # e.g. "ROY AND PAM BROWNE SPRINT"
        prize_pool_text = cells[5].get_text(strip=True) # e.g. "$35,000"

        # Parse placing: "5-13" = 5th of 13, "1-14" = 1st of 14, "U-8" = Unplaced of 8
        finish_pos, field_size = _parse_placing(placing_text)

        # Parse date: "30 May 26" -> 2026-05-30 (assume 20xx)
        race_date = _parse_race_date(date_text)

        # Parse distance: "1200m" -> 1200
        distance_metres = _parse_distance(distance_text)

        # Row 1 (class="odd"): track + condition, class, form, jockey, prize money
        # Note: only 5 cells (not 6) - indices shift by 1
        if len(rows) >= 2:
            second_row = rows[1]
            sec_cells = second_row.find_all(["td", "th"])
            if len(sec_cells) >= 5:
                # First column: "WAIK  Soft5" or "AUCK  Good4"
                track_condition = sec_cells[0].get_text(strip=True) if len(sec_cells) > 0 else ""
                venue, track_condition_text = _parse_track_condition(track_condition)

                # Indices are 1,2,3,4 (not 2,3,4,5) since there are only 5 cells
                race_class = sec_cells[1].get_text(strip=True) if len(sec_cells) > 1 else ""
                form_comment = sec_cells[2].get_text(strip=True) if len(sec_cells) > 2 else ""
                jockey = sec_cells[3].get_text(strip=True) if len(sec_cells) > 3 else ""
                prize_money_text = sec_cells[4].get_text(strip=True) if len(sec_cells) > 4 else ""

                prize_money_nzd = _parse_money(prize_money_text)

                # Row 2: further-detail with barrier, SP, rating, weight, gear
                barrier = None
                sp = None
                rating = None
                weight = None
                gear = None

                if len(rows) >= 3:
                    detail_row = rows[2]
                    detail_cells = detail_row.find_all("td")
                    if detail_cells:
                        detail_text = detail_cells[0].get_text(" ", strip=True)
                        barrier = _extract_detail(detail_text, "Bar:")
                        sp = _extract_detail(detail_text, "SP:")
                        rating = _extract_detail(detail_text, "Rtg:")
                        weight = _extract_detail(detail_text, "Wgt:")
                        gear = _extract_detail(detail_text, "Raceday Gear:")

                # Compute stake_type from finish_position
                if finish_pos == 1:
                    stake_type = "win"
                elif finish_pos in (2, 3):
                    stake_type = "place"
                else:
                    stake_type = "unplaced"

                results.append({
                    "horse_microchip": horse_microchip,
                    "loveracing_id": loveracing_id,
                    "race_date": race_date,
                    "venue": venue,
                    "race_name": race_name,
                    "race_class": race_class,
                    "distance_metres": distance_metres,
                    "field_size": field_size,
                    "barrier": int(barrier) if barrier else None,
                    "jockey": jockey,
                    "finish_position": finish_pos,
                    "prize_money_nzd": prize_money_nzd,
                    "starting_price": sp,
                    "rating": int(rating) if rating and rating.replace("+", "").replace("-", "").isdigit() else None,
                    "weight": float(weight) if weight else None,
                    "gear": gear,
                    "stake_type": stake_type,
                    "source_url": race_history_url(loveracing_id),
                })

    return results


def _parse_placing(text: str) -> tuple[Optional[int], Optional[int]]:
    """
    Parse placing text like '5-13' (5th of 13), '1-14' (won), 'U-8' (unplaced).
    Returns (finish_position, field_size).
    """
    if not text:
        return None, None
    m = re.match(r"(\d+|U)-(\d+)", text.strip())
    if m:
        pos_str, field = m.group(1), int(m.group(2))
        pos = 0 if pos_str == "U" else int(pos_str)
        return pos, field
    return None, None


def _parse_race_date(text: str) -> Optional[date]:
    """Parse race date like '30 May 26' -> 2026-05-30."""
    if not text:
        return None
    # Format: "30 May 26" or "2 May 26"
    months = {
        "jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6,
        "jul": 7, "aug": 8, "sep": 9, "oct": 10, "nov": 11, "dec": 12,
    }
    m = re.match(r"(\d{1,2})\s+([A-Za-z]{3})\s+(\d{2})", text.strip())
    if m:
        day = int(m.group(1))
        mon_abbr = m.group(2).lower()
        year = 2000 + int(m.group(3))
        month = months.get(mon_abbr, 1)
        return date(year, month, day)
    return None


def _parse_distance(text: str) -> Optional[int]:
    """Parse distance like '1200m' -> 1200."""
    if not text:
        return None
    m = re.search(r"(\d+)", text.strip())
    return int(m.group(1)) if m else None


def _parse_track_condition(text: str) -> tuple[str, str]:
    """
    Parse track condition text like 'WAIK  Soft5'.
    Returns (venue, condition).
    """
    if not text:
        return "", ""
    parts = text.split(None, 1)
    venue = parts[0] if parts else ""
    condition = parts[1] if len(parts) > 1 else ""
    return venue, condition


def _parse_money(text: str) -> int:
    """Parse money like '$875' or '$35,000' into cents (integer)."""
    if not text:
        return 0
    # Remove $ and commas, keep digits + decimal
    cleaned = re.sub(r"[^\d.]", "", text)
    if not cleaned:
        return 0
    try:
        dollars = float(cleaned)
        return int(dollars * 100)
    except ValueError:
        return 0


def _extract_detail(text: str, prefix: str) -> Optional[str]:
    """Extract value after a prefix in detail text.
    Handles formats like 'Bar:1' or 'Bar: 1' or 'SP:$8.20' or 'Rtg:67'.
    """
    # Match prefix followed by optional space, then capture until next prefix or end
    # Prefixes: Bar:, SP:, Rtg:, Wgt:, Raceday Gear:
    pattern = re.escape(prefix) + r"\s*([^:\s,]+)"
    m = re.search(pattern, text)
    if m:
        return m.group(1).strip()
    return None


# ── Helpers ─────────────────────────────────────────────────────
def _parse_colour_sex(text: str) -> tuple[Optional[str], Optional[str]]:
    """
    Parse combined colour+sex string like 'Bay Mare' or 'Chestnut Gelding'.
    Returns (colour, sex).
    """
    if not text:
        return None, None

    text = text.strip()
    colours = ["Bay", "Chestnut", "Brown", "Grey", "Black", "Roan"]
    sexes = {
        "colt": ["colt"],
        "filly": ["filly"],
        "gelding": ["gelding"],
        "mare": ["mare"],
        "stallion": ["stallion"],
        "horse": ["horse"],
    }

    found_colour = None
    found_sex = None

    words = text.split()
    for word in words:
        w = word.strip().rstrip(".")
        # Check colour
        for c in colours:
            if w.lower() == c.lower():
                found_colour = c
                break
        # Check sex
        for sex_key, variants in sexes.items():
            if w.lower() in variants:
                found_sex = sex_key
                break

    return found_colour, found_sex


def _parse_nz_date(text: str) -> Optional[date]:
    """Parse NZ date format DD/MM/YYYY."""
    if not text:
        return None
    m = re.match(r"(\d{1,2})\/(\d{1,2})\/(\d{4})", text.strip())
    if m:
        day, month, year = int(m.group(1)), int(m.group(2)), int(m.group(3))
        return date(year, month, day)
    return None


def _name_to_slug(name: Optional[str]) -> str:
    """Convert horse name to URL-safe slug."""
    if not name:
        return ""
    # Remove country suffix and year, then slugify
    # "Prudentia (NZ) 2021" -> "Prudentia-NZ-2021"
    slug = re.sub(r"[^\w\s-]", "", name)
    slug = re.sub(r"\s+", "-", slug.strip())
    return slug


# ── Aggregation ───────────────────────────────────────────────────
def compute_horse_racing_summary(
    races: List[dict],
    horse_microchip: str,
    loveracing_id: int,
    foaling_date: Optional[date] = None,
) -> dict:
    """
    Compute HorseRacingSummary aggregates from a list of RaceResult dicts.

    Args:
        races: List of RaceResult dicts (output from parse_race_history)
        horse_microchip: 15-digit microchip number
        loveracing_id: loveracing.nz HorseID
        foaling_date: Horse's foaling date (for accurate age calculation)

    Returns:
        dict matching HorseRacingSummary fields
    """
    from datetime import datetime

    if not races:
        return {
            "horse_microchip": horse_microchip,
            "loveracing_id": loveracing_id,
            "total_starts": 0,
            "total_wins": 0,
            "total_places": 0,
            "total_earnings_nzd": 0,
            "earnings_by_age": {},
            "earnings_by_class": {},
            "first_start_date": None,
            "last_start_date": None,
            "computed_at": datetime.utcnow(),
        }

    total_starts = len(races)
    total_wins = sum(1 for r in races if r.get("finish_position") == 1)
    total_places = sum(1 for r in races if r.get("finish_position") in (2, 3))
    total_earnings_nzd = sum(r.get("prize_money_nzd", 0) for r in races)

    # Earnings by age (age at race date)
    earnings_by_age: dict[str, int] = {}
    for r in races:
        race_date = r.get("race_date")
        if race_date and isinstance(race_date, date):
            if foaling_date:
                # Calculate actual age at race date
                age = race_date.year - foaling_date.year
                if (race_date.month, race_date.day) < (foaling_date.month, foaling_date.day):
                    age -= 1
            else:
                # Fallback: use calendar year as proxy
                age = race_date.year - 2000
            age_key = str(age)
            earnings_by_age[age_key] = earnings_by_age.get(age_key, 0) + r.get("prize_money_nzd", 0)

    # Earnings by class
    earnings_by_class: dict[str, int] = {}
    for r in races:
        race_class = r.get("race_class") or "Unknown"
        earnings_by_class[race_class] = earnings_by_class.get(race_class, 0) + r.get("prize_money_nzd", 0)

    # Date range
    race_dates = [r.get("race_date") for r in races if r.get("race_date")]
    first_start_date = min(race_dates) if race_dates else None
    last_start_date = max(race_dates) if race_dates else None

    return {
        "horse_microchip": horse_microchip,
        "loveracing_id": loveracing_id,
        "total_starts": total_starts,
        "total_wins": total_wins,
        "total_places": total_places,
        "total_earnings_nzd": total_earnings_nzd,
        "earnings_by_age": earnings_by_age,
        "earnings_by_class": earnings_by_class,
        "first_start_date": first_start_date,
        "last_start_date": last_start_date,
        "computed_at": datetime.utcnow(),
    }
