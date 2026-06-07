#!/usr/bin/env python3
"""
Parse test — First Gear (428364)
"""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

SCRAPLING_VENV = "/home/evo/workspace/DNA/tech-radar/trials/T-2026-008-scrapling/venv"
sp = os.path.join(SCRAPLING_VENV, "lib", f"python{sys.version_info.major}.{sys.version_info.minor}", "site-packages")
if os.path.exists(sp) and sp not in sys.path:
    sys.path.insert(0, sp)

from engines.scrapling import ScraplingEngine
from adapters.loveracing import parse_breeding_page

URL = "https://loveracing.nz/Breeding/428364/First-Gear-NZ-2021.aspx"
ID = 428364

print(f"Fetching: {URL}")
engine = ScraplingEngine()
html = engine.fetch(URL)
print(f"Got {len(html)} chars")

if "First Gear" in html and "LOVERACING.NZ" in html:
    print("✅ Confirmed: real breeding page content\n")
else:
    print("⚠️  May be challenge or error page\n")

ref = parse_breeding_page(html, ID)

print("--- Parsed Fields ---\n")
for k, v in ref.items():
    status = "✅" if v else "❌"
    if k == "pv" and v is False:
        status = "⚪"
    print(f"{status} {k}: {v}")

print("\n✅ Done")
