#!/usr/bin/env python3
"""
Test the race history parser against saved Prudentia HTML.
"""

import sys, os

# Add Scrapling venv for BeautifulSoup
SCRAPLING_VENV = "/home/evo/workspace/DNA/tech-radar/trials/T-2026-008-scrapling/venv"
sp = os.path.join(SCRAPLING_VENV, "lib", f"python{sys.version_info.major}.{sys.version_info.minor}", "site-packages")
if os.path.exists(sp) and sp not in sys.path:
    sys.path.insert(0, sp)

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from adapters.loveracing import parse_race_history

HTML_PATH = "/tmp/evo_racing_data/Prudentia_427416_race_history.html"
MICROCHIP = "985125000126462"
LOVERACING_ID = 427416

print(f"Reading: {HTML_PATH}")
with open(HTML_PATH, "r", encoding="utf-8") as f:
    html = f.read()

print(f"HTML size: {len(html)} chars\n")

races = parse_race_history(html, MICROCHIP, LOVERACING_ID)

print(f"Parsed {len(races)} races\n")

for i, race in enumerate(races):
    print(f"--- Race {i+1} ---")
    print(f"  Date: {race['race_date']}")
    print(f"  Venue: {race['venue']}")
    print(f"  Name: {race['race_name']}")
    print(f"  Class: {race['race_class']}")
    print(f"  Distance: {race['distance_metres']}m")
    print(f"  Field: {race['field_size']}")
    print(f"  Finish: {race['finish_position']}")
    print(f"  Prize: ${race['prize_money_nzd']/100:.2f}")
    print(f"  Jockey: {race['jockey']}")
    print(f"  Barrier: {race['barrier']}")
    print()

# Validate career totals
total_races = len(races)
total_wins = sum(1 for r in races if r["finish_position"] == 1)
total_earnings = sum(r["prize_money_nzd"] for r in races)

print(f"Career totals: {total_races} starts, {total_wins} wins, ${total_earnings/100:.2f} earnings")
print(f"Expected (from page): 9 starts, 2 wins, $36,060.00")

if total_races == 9 and total_wins == 2 and total_earnings == 3606000:
    print("\n✅ ALL VALIDATIONS PASSED")
else:
    print(f"\n⚠️  Mismatch: races={total_races}, wins={total_wins}, earnings=${total_earnings/100:.2f}")
