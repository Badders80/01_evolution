#!/usr/bin/env python3
"""
Debug: check what tables exist in the saved HTML.
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

# Find all tables
tables = soup.find_all("table")
print(f"Total tables: {len(tables)}")

# Check class attributes
for i, t in enumerate(tables[:20]):
    classes = t.get("class", [])
    print(f"Table {i}: classes={classes}")
    if "table-indepth" in classes:
        print(f"  -> MATCH! Rows: {len(t.find_all('tr'))}")

# Try exact match
indepth = soup.find_all("table", class_="table-indepth")
print(f"\nfind_all(class_='table-indepth'): {len(indepth)}")

# Try with lambda
indepth2 = soup.find_all("table", class_=lambda x: x and "table-indepth" in x)
print(f"find_all(lambda): {len(indepth2)}")
