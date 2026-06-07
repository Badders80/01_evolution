#!/usr/bin/env python3
"""
Find the href of the performance-profile link and fetch it.
"""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

SCRAPLING_VENV = "/home/evo/workspace/DNA/tech-radar/trials/T-2026-008-scrapling/venv"
sp = os.path.join(SCRAPLING_VENV, "lib", f"python{sys.version_info.major}.{sys.version_info.minor}", "site-packages")
if os.path.exists(sp) and sp not in sys.path:
    sys.path.insert(0, sp)

from engines.scrapling import ScraplingEngine
from bs4 import BeautifulSoup

URL = "https://loveracing.nz/Breeding/427416/Prudentia-NZ-2021.aspx"

print(f"Fetching: {URL}")
engine = ScraplingEngine()
html = engine.fetch(URL)
print(f"Got {len(html)} chars\n")

soup = BeautifulSoup(html, "lxml")

# Find the performance-profile link
perf_link = soup.find("a", id="performance-profile")
if perf_link:
    href = perf_link.get("href")
    print(f"Performance profile link: {href}")

    # Also check data-url
    data_url = perf_link.get("data-url")
    if data_url:
        print(f"data-url: {data_url}")

    # Fetch the performance profile
    target = data_url or href
    if target:
        if not target.startswith("http"):
            target = "https://loveracing.nz" + target
        print(f"\nFetching: {target}")
        try:
            perf_html = engine.fetch(target)
            print(f"Got {len(perf_html)} chars")

            if len(perf_html) > 1000:
                # Check for race data
                import re
                dates = re.findall(r"\d{1,2}/\d{1,2}/\d{4}", perf_html)
                tracks = ["Te Rapa", "Ellerslie", "Riccarton", "Trentham", "Matamata"]
                found_tracks = [t for t in tracks if t in perf_html]
                print(f"Dates: {len(dates)} — {dates[:20]}")
                print(f"Tracks: {found_tracks}")

                # Look for tables
                perf_soup = BeautifulSoup(perf_html, "lxml")
                tables = perf_soup.find_all("table")
                print(f"Tables: {len(tables)}")
                for i, t in enumerate(tables[:5]):
                    rows = t.find_all("tr")
                    print(f"  Table {i}: {len(rows)} rows")
                    for r in rows[:3]:
                        cells = r.find_all(["td", "th"])
                        print(f"    { [c.get_text(strip=True) for c in cells[:8]] }")

        except Exception as e:
            print(f"Error: {e}")
else:
    print("No performance-profile link found!")
    # List all links with performance in them
    for a in soup.find_all("a", href=re.compile(r"performance", re.I)):
        print(f"  href={a.get('href')} text={a.get_text(strip=True)}")
