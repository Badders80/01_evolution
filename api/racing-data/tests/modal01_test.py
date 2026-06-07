#!/usr/bin/env python3
"""
Test: DisplayContext=Modal01 gives race history, not breeding page.
"""

import sys, os, re
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

SCRAPLING_VENV = "/home/evo/workspace/DNA/tech-radar/trials/T-2026-008-scrapling/venv"
sp = os.path.join(SCRAPLING_VENV, "lib", f"python{sys.version_info.major}.{sys.version_info.minor}", "site-packages")
if os.path.exists(sp) and sp not in sys.path:
    sys.path.insert(0, sp)

from engines.scrapling import ScraplingEngine

engine = ScraplingEngine()

# The user's URL with full params and Modal01
URL = "https://loveracing.nz/Common/SystemTemplates/Modal/EntryDetail.aspx?HorseID=427416&JockeyID=137119&TrackID=15&TrainerID=112312&DisplayContext=Modal01"

print(f"Fetching: {URL}")
html = engine.fetch(URL)
print(f"Got {len(html)} chars\n")

# Check for race data indicators
indicators = {
    "prize_money": "$" in html and "," in html,
    "career_stats": "Career stats" in html,
    "recent_starts": "Recent starts" in html,
    "form": "Form" in html and "X" in html,
    "track_WAIK": "WAIK" in html,
    "track_AUCK": "AUCK" in html,
    "race_date_pattern": len(re.findall(r"\d{1,2}\s+[A-Z][a-z]{2}\s+\d{2}", html)) > 5,
    "rating": "Rating:" in html or "Rtg:" in html,
    "trainer_lance": "Lance" in html or "O'Sullivan" in html,
}

print("--- Race Data Indicators ---\n")
for k, v in indicators.items():
    print(f"{'✅' if v else '❌'} {k}")

# If we have race data, extract some samples
if indicators["career_stats"] or indicators["recent_starts"]:
    print("\n✅ CONFIRMED: This is the race history page!\n")

    # Extract the career stats table
    m = re.search(r"Career\s+\d+\s+\d+.*?(\$[\d,]+\.\d{2})", html)
    if m:
        print(f"Career earnings: {m.group(1)}")

    # Extract recent starts lines
    starts = re.findall(r"\d+-\d+\s+\d{1,2}\s+[A-Z][a-z]{2}\s+\d{2}", html)
    print(f"Recent starts found: {len(starts)}")
    for s in starts[:10]:
        print(f"  {s}")

    # Extract race detail lines
    print("\n--- Sample race entries ---\n")
    lines = html.split("\n")
    for line in lines:
        if re.match(r"\d+-\d+\s+\d{1,2}\s+[A-Z][a-z]{2}\s+\d{2}", line.strip()):
            print(line.strip()[:200])
else:
    print("\n❌ No race data found — still getting breeding page")
