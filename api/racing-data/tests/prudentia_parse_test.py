#!/usr/bin/env python3
"""
Parse test — capture real loveracing.nz HTML and test our BeautifulSoup parser.
"""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Activate Scrapling venv
SCRAPLING_VENV = "/home/evo/workspace/DNA/tech-radar/trials/T-2026-008-scrapling/venv"
sp = os.path.join(SCRAPLING_VENV, "lib", f"python{sys.version_info.major}.{sys.version_info.minor}", "site-packages")
if os.path.exists(sp) and sp not in sys.path:
    sys.path.insert(0, sp)

from engines.scrapling import ScraplingEngine
from adapters.loveracing import parse_breeding_page

URL = "https://loveracing.nz/Breeding/427416/Prudentia-NZ-2021.aspx"
ID = 427416

print(f"Fetching: {URL}")
engine = ScraplingEngine()
html = engine.fetch(URL)
print(f"Got {len(html)} chars")

# Quick sanity: is this the real page?
if "Prudentia (NZ) 2021" in html and "LOVERACING.NZ" in html:
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

# Validate against known values from old SSOT
KNOWN = {
    "microchip": "985125000126462",
    "life_number": "NZ00427416",
    "name": "Prudentia (NZ) 2021",
    "sire_name": "PROISIR (AUS) 2009",
    "dam_name": "LITTLE BIT IRISH (NZ) 2012",
    "colour": "Bay",
    "sex": "mare",  # Now 4YO, so listed as Mare not Filly
    "breeder": "Goldeye Trust",
}

print("\n--- Validation ---\n")
all_ok = True
for field, expected in KNOWN.items():
    actual = ref.get(field)
    if actual == expected:
        print(f"✅ {field}: '{actual}' matches expected")
    else:
        print(f"❌ {field}: got '{actual}', expected '{expected}'")
        all_ok = False

print(f"\n{'✅ All validations passed' if all_ok else '❌ Some validations failed'}")
