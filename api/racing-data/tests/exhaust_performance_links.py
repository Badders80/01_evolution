#!/usr/bin/env python3
"""
Exhaust all performance/profile link variants on loveracing.nz.
The breeding page has "Horse Performance Profile ›" links — find the right one.
"""

import sys, os, re
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

SCRAPLING_VENV = "/home/evo/workspace/DNA/tech-radar/trials/T-2026-008-scrapling/venv"
sp = os.path.join(SCRAPLING_VENV, "lib", f"python{sys.version_info.major}.{sys.version_info.minor}", "site-packages")
if os.path.exists(sp) and sp not in sys.path:
    sys.path.insert(0, sp)

from engines.scrapling import ScraplingEngine
from bs4 import BeautifulSoup

URL = "https://loveracing.nz/Breeding/427416/Prudentia-NZ-2021.aspx"

engine = ScraplingEngine()
html = engine.fetch(URL)
print(f"Breeding page: {len(html)} chars\n")

soup = BeautifulSoup(html, "lxml")

# Find ALL links that mention performance or profile
print("=== ALL performance/profile links on breeding page ===\n")
links = []
for a in soup.find_all("a"):
    text = a.get_text(strip=True)
    href = a.get("href", "")
    data_url = a.get("data-url", "")
    classes = a.get("class", [])
    _id = a.get("id", "")

    if any(k in text.lower() for k in ["performance", "profile", "form", "result"]) \
       or any(k in href.lower() for k in ["performance", "profile", "form", "result", "entrydetail"]) \
       or any(k in str(classes).lower() for k in ["performance", "profile"]):
        links.append({
            "text": text,
            "href": href,
            "data_url": data_url,
            "classes": classes,
            "id": _id,
        })
        print(f"  text='{text[:60]}'")
        print(f"    href={href}")
        if data_url:
            print(f"    data-url={data_url}")
        print(f"    classes={classes} id={_id}")
        print()

# Now try fetching each unique href
print("\n=== Fetching each unique performance URL ===\n")
seen = set()
for link in links:
    target = link["data_url"] or link["href"]
    if not target or target in seen:
        continue
    seen.add(target)

    # Build absolute URL
    if target.startswith("/"):
        target = "https://loveracing.nz" + target

    print(f"\nFetching: {target}")
    try:
        page_html = engine.fetch(target)

        # Analyze response
        is_breeding = "Prudentia (NZ) 2021" in page_html and "LOVERACING.NZ" in page_html and "Bay Mare" in page_html
        is_error = "Error" in page_html[:2000] or page_html.count("<body") == 0

        import re
        dates = re.findall(r"\d{1,2}/\d{1,2}/\d{4}", page_html)
        tracks = ["Te Rapa", "Ellerslie", "Riccarton", "Trentham", "Matamata", "Awapuni", "Wanganui", "Hastings"]
        found_tracks = [t for t in tracks if t in page_html]
        money = re.findall(r"\$[\d,]+\.\d{2}", page_html)

        # Look for race-specific terms
        has_races = len(dates) > 5 and len(found_tracks) > 1

        if is_error:
            print(f"  ❌ Error page ({len(page_html)} chars)")
        elif is_breeding and not has_races:
            print(f"  🔄 Same breeding page ({len(page_html)} chars, {len(dates)} dates, tracks: {found_tracks})")
        elif has_races:
            print(f"  ✅ LIKELY RACE DATA! ({len(page_html)} chars)")
            print(f"     Dates: {len(dates)} | Tracks: {found_tracks} | Money: {len(money)}")
            # Save it
            slug = re.sub(r'[^\w]', '_', link["text"][:30])
            with open(f"/tmp/loveracing_perf_{slug}.html", "w") as f:
                f.write(page_html)
            print(f"     Saved to /tmp/loveracing_perf_{slug}.html")

            # Show first table
            p_soup = BeautifulSoup(page_html, "lxml")
            tables = p_soup.find_all("table")
            if tables:
                t = tables[0]
                rows = t.find_all("tr")
                print(f"     First table: {len(rows)} rows")
                for r in rows[:5]:
                    cells = r.find_all(["td", "th"])
                    print(f"       { [c.get_text(strip=True) for c in cells[:10]] }")
        else:
            print(f"  ⚪ Unclear ({len(page_html)} chars, {len(dates)} dates, tracks: {found_tracks})")

    except Exception as e:
        print(f"  ❌ Fetch failed: {type(e).__name__}: {str(e)[:100]}")

print("\n=== Done ===")
