#!/usr/bin/env python3
"""
Engine smoke test — run from api/racing-data/

Tests Scrapling (local, no API key) against:
  1. example.com — should always work
  2. loveracing.nz breeding page — the real target

If Scrapling fails on loveracing.nz, we need Webclaw Cloud key.
"""

import sys, os

# Add parent directory (racing-data/) to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Activate Scrapling venv
SCRAPLING_VENV = "/home/evo/workspace/DNA/tech-radar/trials/T-2026-008-scrapling/venv"
sp = os.path.join(SCRAPLING_VENV, "lib", f"python{sys.version_info.major}.{sys.version_info.minor}", "site-packages")
if os.path.exists(sp) and sp not in sys.path:
    sys.path.insert(0, sp)

from engines.scrapling import ScraplingEngine

URLS = [
    ("example.com", "https://example.com/"),
    ("Prudentia breeding", "https://loveracing.nz/Breeding/427416/Prudentia-NZ-2021.aspx"),
]

engine = ScraplingEngine()

for name, url in URLS:
    print(f"\n{'='*60}")
    print(f"Testing: {name}")
    print(f"URL: {url}")
    print(f"{'='*60}")
    try:
        html = engine.fetch(url)
        print(f"✅ Success — {len(html)} chars")
        # Check if we got Cloudflare challenge
        if "challenge" in html.lower() or "cloudflare" in html.lower():
            print("⚠️  Got Cloudflare challenge page — need Webclaw or better stealth")
        elif "loveracing" in html.lower() or "prudentia" in html.lower():
            print("✅ Page content looks correct")
        elif "example domain" in html.lower():
            print("✅ Page content looks correct")
        print(html[:800])  # First 800 chars
    except Exception as e:
        print(f"❌ Failed: {type(e).__name__}: {e}")

print("\n" + "="*60)
print("Done")
