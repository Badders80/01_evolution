#!/usr/bin/env python3
"""
Test: What minimal URL gives race history? Try different param combinations.
"""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

SCRAPLING_VENV = "/home/evo/workspace/DNA/tech-radar/trials/T-2026-008-scrapling/venv"
sp = os.path.join(SCRAPLING_VENV, "lib", f"python{sys.version_info.major}.{sys.version_info.minor}", "site-packages")
if os.path.exists(sp) and sp not in sys.path:
    sys.path.insert(0, sp)

from engines.scrapling import ScraplingEngine

engine = ScraplingEngine()

TESTS = [
    ("Full params (user URL)", "https://loveracing.nz/Common/SystemTemplates/Modal/EntryDetail.aspx?HorseID=427416&JockeyID=137119&TrackID=15&TrainerID=112312&DisplayContext=Modal01"),
    ("HorseID only + Modal01", "https://loveracing.nz/Common/SystemTemplates/Modal/EntryDetail.aspx?HorseID=427416&DisplayContext=Modal01"),
    ("HorseID + TrainerID + Modal01", "https://loveracing.nz/Common/SystemTemplates/Modal/EntryDetail.aspx?HorseID=427416&TrainerID=112312&DisplayContext=Modal01"),
    ("HorseID + JockeyID + Modal01", "https://loveracing.nz/Common/SystemTemplates/Modal/EntryDetail.aspx?HorseID=427416&JockeyID=137119&DisplayContext=Modal01"),
    ("Modal (not Modal01)", "https://loveracing.nz/Common/SystemTemplates/Modal/EntryDetail.aspx?HorseID=427416&DisplayContext=Modal"),
]

for label, url in TESTS:
    print(f"\n{'='*60}")
    print(f"Test: {label}")
    print(f"URL: {url}")
    try:
        html = engine.fetch(url)
        is_race = "Career stats" in html and "Recent starts" in html
        is_breed = "Bay Mare" in html and "LOVERACING.NZ" in html
        print(f"Result: {'✅ Race history' if is_race else '🔄 Breeding page' if is_breed else '⚪ Unknown'} ({len(html)} chars)")
    except Exception as e:
        print(f"❌ Error: {e}")
