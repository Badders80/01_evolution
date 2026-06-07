#!/usr/bin/env python3
"""
Diagnostic: find where known values live in the loveracing.nz HTML.
Search for known Prudentia values to understand DOM structure.
"""

import sys, os, re
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

SCRAPLING_VENV = "/home/evo/workspace/DNA/tech-radar/trials/T-2026-008-scrapling/venv"
sp = os.path.join(SCRAPLING_VENV, "lib", f"python{sys.version_info.major}.{sys.version_info.minor}", "site-packages")
if os.path.exists(sp) and sp not in sys.path:
    sys.path.insert(0, sp)

from engines.scrapling import ScraplingEngine

URL = "https://loveracing.nz/Breeding/427416/Prudentia-NZ-2021.aspx"
ID = 427416

print(f"Fetching: {URL}")
engine = ScraplingEngine()
html = engine.fetch(URL)
print(f"Got {len(html)} chars\n")

# Known values from old SSOT_Build record
KNOWN = {
    "microchip": "985125000126462",
    "life_number": "NZ00427416",
    "born_day": "13/11/2021",
    "born_iso": "2021-11-13",
    "sex": "Filly",
    "colour": "Bay",
    "sire": "PROISIR",
    "dam": "LITTLE BIT IRISH",
    "breeder": "Goldeye Trust",
}

print("--- Searching for known values in HTML ---\n")
for label, value in KNOWN.items():
    if value in html:
        # Find context around the match
        idx = html.find(value)
        start = max(0, idx - 200)
        end = min(len(html), idx + len(value) + 200)
        context = html[start:end]
        print(f"✅ {label} = '{value}' found at index {idx}")
        print(f"   Context: ...{context}...")
        print()
    else:
        print(f"❌ {label} = '{value}' NOT found")
        print()

# Also search for JSON/script blocks that might contain structured data
print("--- Looking for JSON data blocks ---\n")
json_blocks = re.findall(r'<script[^>]*>(.*?)</script>', html, re.DOTALL)
print(f"Found {len(json_blocks)} script blocks")
for i, block in enumerate(json_blocks[:5]):
    if len(block) > 100:
        print(f"\nScript block {i} ({len(block)} chars):")
        # Look for any known value
        for label, value in KNOWN.items():
            if value in block:
                print(f"  -> Contains {label}: {value}")
