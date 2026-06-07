#!/usr/bin/env python3
"""
Probe 2: look for race history tabs and dynamic load mechanisms.
"""

import sys, os, re, json
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

SCRAPLING_VENV = "/home/evo/workspace/DNA/tech-radar/trials/T-2026-008-scrapling/venv"
sp = os.path.join(SCRAPLING_VENV, "lib", f"python{sys.version_info.major}.{sys.version_info.minor}", "site-packages")
if os.path.exists(sp) and sp not in sys.path:
    sys.path.insert(0, sp)

from engines.scrapling import ScraplingEngine
from bs4 import BeautifulSoup

URL = "https://loveracing.nz/Breeding/427416/Prudentia-NZ-2021.aspx"

print(f"Fetching: {URL}")
engine = ScraplingEngine()
html = engine.fetch(URL)
print(f"Got {len(html)} chars\n")

soup = BeautifulSoup(html, "lxml")

# Look for tab navigation
print("--- Tab navigation ---\n")
for nav in soup.find_all("ul", class_=re.compile(r"nav|tabs|menu")):
    links = nav.find_all("a")
    if links:
        print(f"Nav: { [a.get_text(strip=True) for a in links[:12]] }")

# Look for data-url attributes
print("\n--- data-url attributes ---\n")
for tag in soup.find_all(attrs={"data-url": True}):
    print(f"  {tag.name}: data-url={tag.get('data-url')}")

for tag in soup.find_all(attrs={"href": True}):
    href = tag.get("href", "")
    if "form" in href.lower() or "result" in href.lower() or "entry" in href.lower():
        if "modal" in href.lower() or "ajax" in href.lower():
            print(f"  {tag.name}: href={href}")

# Look in all script tags for URLs containing horse data
print("\n--- Script tag URLs ---\n")
for script in soup.find_all("script"):
    text = script.string or ""
    if "427416" in text or "HorseID" in text:
        # Find any URLs
        urls = re.findall(r'["\']([^"\']*427416[^"\']*)["\']', text)
        for u in urls[:10]:
            print(f"  URL in script: {u}")
        # Look for any loadForm or loadResults function calls
        if "load" in text.lower():
            lines = text.split("\n")
            for line in lines:
                if "load" in line.lower() and ("form" in line.lower() or "result" in line.lower()):
                    print(f"  Code line: {line.strip()[:200]}")

# Look for iframe or modal content
print("\n--- Iframes / Modals ---\n")
for iframe in soup.find_all("iframe"):
    print(f"  iframe src={iframe.get('src')}")

# Check if there's a separate form/results page
print("\n--- Direct URL probe ---\n")
# The loveracing.nz site might have a separate results page
possible_urls = [
    f"https://loveracing.nz/Breeding/427416/Prudentia-NZ-2021.aspx#form",
    f"https://loveracing.nz/Breeding/427416/Prudentia-NZ-2021.aspx#results",
    f"https://loveracing.nz/Common/Ajax/HorseForm.aspx?HorseID=427416",
    f"https://loveracing.nz/Common/Ajax/HorseResults.aspx?HorseID=427416",
]
for test_url in possible_urls:
    try:
        test_html = engine.fetch(test_url)
        print(f"  {test_url}: {len(test_html)} chars")
        # Check if it has race data
        if re.search(r"\d{1,2}/\d{1,2}/\d{4}", test_html):
            dates = re.findall(r"\d{1,2}/\d{1,2}/\d{4}", test_html)
            print(f"    -> Contains dates: {len(dates)} found")
        if "Te Rapa" in test_html or "Ellerslie" in test_html:
            print(f"    -> Contains track names")
    except Exception as e:
        print(f"  {test_url}: ERROR {e}")
