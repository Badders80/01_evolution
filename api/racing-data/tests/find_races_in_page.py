#!/usr/bin/env python3
"""
Search the breeding page HTML for embedded race history data.
Look for performance sections, form tables, or race result blocks.
"""

import sys, os, re
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

# Look for "performance" or "form" in IDs or classes
print("--- Sections with performance/form IDs ---\n")
for tag in soup.find_all(id=re.compile(r"performance|form|result|record", re.I)):
    print(f"  id={tag.get('id')} tag={tag.name} classes={tag.get('class')}")

print("\n--- Divs with performance/form classes ---\n")
for tag in soup.find_all(class_=re.compile(r"performance|form|result|record", re.I)):
    print(f"  class={tag.get('class')} id={tag.get('id')} tag={tag.name}")

# Look for tab content panels
print("\n--- Tab content panels ---\n")
for tag in soup.find_all(class_="tab-content"):
    tab_id = tag.get("id", "no-id")
    print(f"  tab-content id={tab_id}")
    # Check if it has tables
    tables = tag.find_all("table")
    if tables:
        print(f"    -> {len(tables)} tables")
        for t in tables:
            rows = t.find_all("tr")
            print(f"       table: {len(rows)} rows")
            # Print first few rows
            for r in rows[:3]:
                cells = r.find_all(["td", "th"])
                print(f"         { [c.get_text(strip=True) for c in cells[:8]] }")

# Search raw HTML for "Maiden" or race class terms
print("\n--- Race class terms in HTML ---\n")
classes = ["Maiden", "Open", "Group 1", "Group 2", "Group 3", "Listed", "Handicap", "Stakes"]
for rc in classes:
    count = html.count(rc)
    if count > 0:
        print(f"  {rc}: {count} occurrences")

# Look for specific race dates we know about (from the user's knowledge)
# Prudentia's recent win at Te Rapa in April 2026? Let me search for "2026"
print("\n--- Recent year mentions ---\n")
for year in ["2026", "2025", "2024", "2023", "2022"]:
    count = html.count(year)
    if count > 0:
        print(f"  {year}: {count} occurrences")
