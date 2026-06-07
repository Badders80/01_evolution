#!/usr/bin/env python3
"""
Inspect the HorseResults.aspx response for race history data.
"""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

SCRAPLING_VENV = "/home/evo/workspace/DNA/tech-radar/trials/T-2026-008-scrapling/venv"
sp = os.path.join(SCRAPLING_VENV, "lib", f"python{sys.version_info.major}.{sys.version_info.minor}", "site-packages")
if os.path.exists(sp) and sp not in sys.path:
    sys.path.insert(0, sp)

from engines.scrapling import ScraplingEngine

URL = "https://loveracing.nz/Common/Ajax/HorseResults.aspx?HorseID=427416"

print(f"Fetching: {URL}")
engine = ScraplingEngine()
html = engine.fetch(URL)
print(f"Got {len(html)} chars\n")

# Check what's in there
if len(html) > 1000:
    print("First 1500 chars:")
    print(html[:1500])
    print("\n...")
    print("\nLast 800 chars:")
    print(html[-800:])

    # Count tables
    import re
    tables = html.count("<table")
    print(f"\nTables found: {tables}")

    # Look for race date patterns
    dates = re.findall(r"\d{1,2}/\d{1,2}/\d{4}", html)
    print(f"Date strings: {len(dates)} — {dates[:20]}")

    # Look for track names
    tracks = ["Te Rapa", "Ellerslie", "Riccarton", "Trentham", "Matamata", "Awapuni"]
    found = [t for t in tracks if t in html]
    print(f"Tracks found: {found}")

    # Look for prize money
    money = re.findall(r"\$[\d,]+\.\d{2}", html)
    print(f"Money strings: {len(money)} — {money[:10]}")

    # Look for position numbers
    positions = re.findall(r"<td>\s*(\d+)\s*</td>", html)
    print(f"Position-like cells: {len(positions)} — {positions[:20]}")
