#!/usr/bin/env python3
"""
Debug: trace through one table to see why parser skips it.
"""

import sys, os

SCRAPLING_VENV = "/home/evo/workspace/DNA/tech-radar/trials/T-2026-008-scrapling/venv"
sp = os.path.join(SCRAPLING_VENV, "lib", f"python{sys.version_info.major}.{sys.version_info.minor}", "site-packages")
if os.path.exists(sp) and sp not in sys.path:
    sys.path.insert(0, sp)

from bs4 import BeautifulSoup

HTML_PATH = "/tmp/evo_racing_data/Prudentia_427416_race_history.html"

with open(HTML_PATH, "r", encoding="utf-8") as f:
    html = f.read()

soup = BeautifulSoup(html, "lxml")
tables = soup.find_all("table", class_="table-indepth")

print(f"Found {len(tables)} tables\n")

# Inspect first table in detail
t = tables[0]
rows = t.find_all("tr")
print(f"First table: {len(rows)} rows")

for i, row in enumerate(rows):
    cells = row.find_all(["td", "th"])
    texts = [c.get_text(strip=True) for c in cells]
    print(f"  Row {i}: {len(cells)} cells = {texts}")
    # Show raw HTML for first row
    if i == 0:
        print(f"    Raw: {row.prettify()[:500]}")
