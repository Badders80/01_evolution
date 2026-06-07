#!/usr/bin/env python3
"""
Find the race results/form page for Prudentia.
Try common URL patterns.
"""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

SCRAPLING_VENV = "/home/evo/workspace/DNA/tech-radar/trials/T-2026-008-scrapling/venv"
sp = os.path.join(SCRAPLING_VENV, "lib", f"python{sys.version_info.major}.{sys.version_info.minor}", "site-packages")
if os.path.exists(sp) and sp not in sys.path:
    sys.path.insert(0, sp)

from engines.scrapling import ScraplingEngine

BASE = "https://loveracing.nz"
ID = 427416
SLUG = "Prudentia-NZ-2021"

PATTERNS = [
    f"{BASE}/Performance/{ID}/{SLUG}.aspx",
    f"{BASE}/Profiles/{ID}/{SLUG}.aspx",
    f"{BASE}/Profiles/Horse/{ID}/{SLUG}.aspx",
    f"{BASE}/Horse/{ID}/{SLUG}.aspx",
    f"{BASE}/Horses/{ID}/{SLUG}.aspx",
    f"{BASE}/Results/{ID}/{SLUG}.aspx",
    f"{BASE}/Form/{ID}/{SLUG}.aspx",
    f"{BASE}/RaceRecord/{ID}/{SLUG}.aspx",
    f"{BASE}/Common/SystemTemplates/Modal/EntryDetail.aspx?HorseID={ID}&DisplayContext=Modal",
    f"{BASE}/Common/Ajax/HorseForm.aspx?HorseID={ID}",
]

engine = ScraplingEngine()

for url in PATTERNS:
    try:
        html = engine.fetch(url)
        # Check if it's a real page with horse data
        has_prudentia = "Prudentia" in html
        has_dates = len(__import__('re').findall(r"\d{1,2}/\d{1,2}/\d{4}", html)) > 2
        has_tracks = "Te Rapa" in html or "Ellerslie" in html or "Riccarton" in html

        status = "❌"
        if has_prudentia and (has_dates or has_tracks):
            status = "✅ LIKELY RESULTS PAGE"
        elif has_prudentia:
            status = "🟡 Has Prudentia but no race data"
        elif len(html) > 50000:
            status = "🟡 Large response"

        print(f"{status} {url}")
        print(f"    Size: {len(html)} | Prudentia: {has_prudentia} | Dates: {has_dates} | Tracks: {has_tracks}")

        if has_prudentia and (has_dates or has_tracks):
            print(f"    -> Saving for inspection")
            with open(f"/tmp/loveracing_{ID}_results.html", "w") as f:
                f.write(html)

    except Exception as e:
        print(f"❌ {url}: {type(e).__name__}: {str(e)[:80]}")
