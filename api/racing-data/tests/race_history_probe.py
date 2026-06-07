#!/usr/bin/env python3
"""
Probe: find race history data in the breeding page HTML.
Search for race result tables, race date patterns, or AJAX endpoints.
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

# Look for race-related tabs or sections
print("--- Race-related elements ---\n")

# Tabs
for tab in soup.find_all("a", href=re.compile(r"#(results|form|races|history)")):
    print(f"Tab: {tab.get_text(strip=True)} -> {tab.get('href')}")

# Look for tables
tables = soup.find_all("table")
print(f"\nFound {len(tables)} tables")
for i, table in enumerate(tables[:10]):
    caption = table.find("caption")
    header_cells = table.find_all("th")
    headers = [th.get_text(strip=True) for th in header_cells[:8]]
    print(f"  Table {i}: caption='{caption.get_text(strip=True) if caption else 'None'}' headers={headers}")
    rows = table.find_all("tr")
    print(f"    Rows: {len(rows)}")
    if rows and i < 3:
        for row in rows[:3]:
            cells = row.find_all(["td", "th"])
            print(f"      { [c.get_text(strip=True) for c in cells[:6]] }")

# Look for race date patterns
print("\n--- Race date patterns ---\n")
date_pattern = r"\d{1,2}/\d{1,2}/\d{4}"
dates = re.findall(date_pattern, html)
print(f"Found {len(dates)} date strings")
unique_dates = sorted(set(dates))
print(f"Unique dates: {unique_dates[:20]}")

# Look for track names
tracks = ["Ellerslie", "Te Rapa", "Riccarton", "Trentham", "Ruakaka", "Matamata", "Awapuni", "Otaki", "Foxton", "Waverley", "New Plymouth", "Pukekohe", "Rotorua", "Wanganui", "Hastings", "Palmerston North", "Wellington", "Oamaru", "Gore", "Invercargill", "Ashburton", "Timaru", "Cromwell", "Kurow", "Masterton", "Tauherenikau", "Wingatui"]
found_tracks = [t for t in tracks if t.lower() in html.lower()]
print(f"\nTracks mentioned: {found_tracks}")

# Look for AJAX endpoints
print("\n--- AJAX endpoints ---\n")
for script in soup.find_all("script"):
    text = script.string or ""
    for match in re.findall(r'["\']([^"\']*EntryDetail[^"\']*)["\']', text):
        print(f"  EntryDetail endpoint: {match}")
    for match in re.findall(r'["\']([^"\']*GetForm[^"\']*)["\']', text):
        print(f"  GetForm endpoint: {match}")
    for match in re.findall(r'["\']([^"\']*GetResults[^"\']*)["\']', text):
        print(f"  GetResults endpoint: {match}")
