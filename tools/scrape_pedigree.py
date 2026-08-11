#!/usr/bin/env python3
"""
scrape_pedigree.py — Scrape full pedigree from loveracing.nz breeding page.

Parses Dam Line and Sire Line tables into structured JSON and writes
to horses/{slug}/pedigree.json (merges with existing data).

Usage:
    python3 tools/scrape_pedigree.py <slug>
    python3 tools/scrape_pedigree.py --all
"""

import json
import re
import sys
import urllib.request
from pathlib import Path
from html.parser import HTMLParser

EVOLUTION_DIR = Path(__file__).resolve().parent.parent
HORSES_DIR = EVOLUTION_DIR / "horses"


class PedigreeTableParser(HTMLParser):
    """Parse the Dam Line and Sire Line tables from loveracing.nz."""

    def __init__(self):
        super().__init__()
        self.in_table = False
        self.in_row = False
        self.in_cell = False
        self.in_link = False
        self.current_table = None  # "dam_line" or "sire_line"
        self.current_row = []
        self.current_cell_text = ""
        self.current_cell_href = ""
        self.current_horse_id = None
        self.tables = {"dam_line": [], "sire_line": []}
        self._seen_h2 = ""
        self._in_h2 = False
        self._in_th = False

    def handle_starttag(self, tag, attrs):
        attrs_dict = dict(attrs)
        if tag == "h2":
            self._in_h2 = True
            self._seen_h2 = ""
        elif tag == "table":
            self.in_table = True
        elif tag == "tr" and self.in_table:
            self.in_row = True
            self.current_row = []
        elif tag in ("td", "th") and self.in_row:
            self.in_cell = True
            self.current_cell_text = ""
            self.current_cell_href = ""
            self.current_horse_id = None
            if tag == "th":
                self._in_th = True
        elif tag == "a" and self.in_cell:
            self.in_link = True
            href = attrs_dict.get("href", "")
            # Extract HorseID from URL like EntryDetail.aspx?HorseID=271437
            m = re.search(r"HorseID=(\d+)", href)
            if m:
                self.current_horse_id = int(m.group(1))

    def handle_endtag(self, tag):
        if tag == "h2":
            self._in_h2 = False
            h = self._seen_h2.strip().lower()
            if "dam line" in h:
                self.current_table = "dam_line"
            elif "sire line" in h:
                self.current_table = "sire_line"
        elif tag == "table":
            self.in_table = False
            self.current_table = None
        elif tag == "tr":
            if self.in_row and self.current_row:
                # Only add rows that have horse name data (skip headers)
                if self.current_table and len(self.current_row) >= 1:
                    self.tables[self.current_table].append(self.current_row)
            self.in_row = False
        elif tag in ("td", "th"):
            if self.in_cell:
                cell = {
                    "name": self.current_cell_text.strip(),
                    "horse_id": self.current_horse_id,
                    "href": self.current_cell_href,
                }
                self.current_row.append(cell)
                self.current_cell_text = ""
                self.current_cell_href = ""
                self.current_horse_id = None
            self.in_cell = False
            self._in_th = False
        elif tag == "a":
            self.in_link = False

    def handle_data(self, data):
        if self._in_h2:
            self._seen_h2 += data
        if self.in_cell:
            self.current_cell_text += data


def parse_name(name: str) -> dict:
    """Parse 'Whiffle (USA) 2004' into {name, country, year}."""
    if not name or name == "—":
        return {"name": "—", "country": "", "year": ""}
    name = name.strip()
    m = re.match(r"^(.+?)\s*\(([A-Z]{2,4})\)\s*(\d{4})?", name)
    if m:
        return {"name": m.group(1).strip(), "country": m.group(2), "year": m.group(3) or ""}
    return {"name": name, "country": "", "year": ""}


def scrape_pedigree(loveracing_id: int, horse_name: str = "") -> str:
    """Fetch and return raw HTML from loveracing.nz breeding page."""
    import urllib.parse
    slug_name = urllib.parse.quote(horse_name) if horse_name else str(loveracing_id)
    url = f"https://loveracing.nz/Breeding/{loveracing_id}/{slug_name}.aspx"
    print(f"  Fetching: {url}")
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        html = resp.read().decode("utf-8", errors="replace")
    return html


def parse_pedigree_tables(html: str) -> dict:
    """Parse HTML and extract dam_line and sire_line arrays."""
    parser = PedigreeTableParser()
    parser.feed(html)

    result = {"dam_line": [], "sire_line": []}

    for table_key in ("dam_line", "sire_line"):
        rows = parser.tables.get(table_key, [])
        for row in rows:
            # Row cells: [horse_cell, relation_cell, sire_or_dam_cell]
            # Dam Line: mare | by | sire_of_broodmare
            # Sire Line: sire | from | dam_of_sire
            if len(row) < 1:
                continue

            horse_cell = row[0]
            horse_parsed = parse_name(horse_cell["name"])

            partner_cell = row[2] if len(row) >= 3 else {"name": "", "horse_id": None}
            partner_parsed = parse_name(partner_cell.get("name", "")) if isinstance(partner_cell, dict) else {"name": "", "country": "", "year": ""}

            entry = {
                "name": horse_parsed["name"],
                "country": horse_parsed["country"],
                "year": horse_parsed["year"],
                "horse_id": horse_cell.get("horse_id"),
                "partner": {
                    "name": partner_parsed.get("name", ""),
                    "country": partner_parsed.get("country", ""),
                    "year": partner_parsed.get("year", ""),
                    "horse_id": partner_cell.get("horse_id") if isinstance(partner_cell, dict) else None,
                },
            }
            result[table_key].append(entry)

    return result


def update_pedigree_json(slug: str, pedigree_data: dict) -> None:
    """Merge scraped pedigree into existing horses/{slug}/pedigree.json."""
    pedigree_path = HORSES_DIR / slug / "pedigree.json"
    if pedigree_path.exists():
        with pedigree_path.open("r", encoding="utf-8") as f:
            existing = json.load(f)
    else:
        existing = {}

    # Merge in dam_line and sire_line
    existing["dam_line"] = pedigree_data["dam_line"]
    existing["sire_line"] = pedigree_data["sire_line"]

    # Update sire/dam top-level fields from the first entry if missing
    if pedigree_data["sire_line"] and not existing.get("sire", {}).get("name"):
        s = pedigree_data["sire_line"][0]
        existing["sire"] = {"name": f"{s['name']} ({s['country']}) {s['year']}", "sire_id": s.get("horse_id")}
    if pedigree_data["dam_line"] and not existing.get("dam", {}).get("name"):
        d = pedigree_data["dam_line"][0]
        existing["dam"] = {"name": f"{d['name']} ({d['country']}) {d['year']}", "dam_id": d.get("horse_id")}

    with pedigree_path.open("w", encoding="utf-8") as f:
        json.dump(existing, f, indent=2, ensure_ascii=False)

    print(f"  ✅ Updated {pedigree_path}")
    print(f"     dam_line: {len(pedigree_data['dam_line'])} generations")
    print(f"     sire_line: {len(pedigree_data['sire_line'])} generations")


def process_horse(slug: str) -> bool:
    """Scrape pedigree for one horse. Returns True on success."""
    pedigree_path = HORSES_DIR / slug / "pedigree.json"
    if not pedigree_path.exists():
        print(f"  ❌ No pedigree.json found for {slug}")
        return False

    with pedigree_path.open("r", encoding="utf-8") as f:
        existing = json.load(f)

    loveracing_id = existing.get("loveracing_id")
    if not loveracing_id:
        print(f"  ❌ No loveracing_id in {slug}/pedigree.json")
        return False

    horse_name = existing.get("horse_name", slug)
    print(f"\n📋 Scraping pedigree for {horse_name} (loveracing_id={loveracing_id})")

    try:
        html = scrape_pedigree(loveracing_id, horse_name)
        pedigree_data = parse_pedigree_tables(html)

        if not pedigree_data["dam_line"] and not pedigree_data["sire_line"]:
            print(f"  ⚠️  No pedigree tables found — page may require JS or structure changed")
            return False

        update_pedigree_json(slug, pedigree_data)
        return True
    except Exception as e:
        print(f"  ❌ Error: {e}")
        return False


def main():
    if len(sys.argv) < 2:
        print("Usage: python3 tools/scrape_pedigree.py <slug>")
        print("       python3 tools/scrape_pedigree.py --all")
        sys.exit(1)

    arg = sys.argv[1]

    if arg == "--all":
        slugs = [d.name for d in HORSES_DIR.iterdir() if d.is_dir() and (d / "pedigree.json").exists()]
        print(f"Found {len(slugs)} horses with pedigree.json")
        success = 0
        for slug in sorted(slugs):
            if process_horse(slug):
                success += 1
        print(f"\n{'='*60}")
        print(f"Done: {success}/{len(slugs)} horses scraped successfully")
    else:
        process_horse(arg)


if __name__ == "__main__":
    main()