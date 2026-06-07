#!/usr/bin/env python3
"""
Probe the RaceInfo/Horses.aspx page — it might have horse search + race records.
"""

import sys, os, re
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

SCRAPLING_VENV = "/home/evo/workspace/DNA/tech-radar/trials/T-2026-008-scrapling/venv"
sp = os.path.join(SCRAPLING_VENV, "lib", f"python{sys.version_info.major}.{sys.version_info.minor}", "site-packages")
if os.path.exists(sp) and sp not in sys.path:
    sys.path.insert(0, sp)

from engines.scrapling import ScraplingEngine
from bs4 import BeautifulSoup

engine = ScraplingEngine()

# Try RaceInfo/Horses.aspx with search parameter
URLS = [
    "https://loveracing.nz/raceinfo/Horses.aspx",
    "https://loveracing.nz/RaceInfo/Horses.aspx?q=Prudentia",
    "https://loveracing.nz/RaceInfo/Horses.aspx?search=Prudentia",
    "https://loveracing.nz/RaceInfo/Horses.aspx?horse=427416",
    "https://loveracing.nz/RaceInfo/Horses.aspx?horseID=427416",
]

for url in URLS:
    try:
        html = engine.fetch(url)
        print(f"\n{url}")
        print(f"  Size: {len(html)}")

        # Look for search results or horse listings
        soup = BeautifulSoup(html, "lxml")
        tables = soup.find_all("table")
        print(f"  Tables: {len(tables)}")

        # Check if Prudentia is mentioned
        has_prudentia = "Prudentia" in html
        print(f"  Has Prudentia: {has_prudentia}")

        # Look for date patterns
        dates = re.findall(r"\d{1,2}/\d{1,2}/\d{4}", html)
        print(f"  Dates: {len(dates)}")

        if tables and has_prudentia:
            for t in tables[:3]:
                rows = t.find_all("tr")
                if len(rows) > 1:
                    print(f"    Table ({len(rows)} rows):")
                    for r in rows[:5]:
                        cells = r.find_all(["td", "th"])
                        texts = [c.get_text(strip=True) for c in cells[:10]]
                        if any("Prudentia" in t for t in texts):
                            print(f"      -> {texts}")

    except Exception as e:
        print(f"\n{url}: ERROR {e}")
