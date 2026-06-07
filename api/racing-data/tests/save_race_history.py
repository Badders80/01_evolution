#!/usr/bin/env python3
"""
Save raw race history HTML for both pilot horses.
These become our parsing reference samples.
"""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

SCRAPLING_VENV = "/home/evo/workspace/DNA/tech-radar/trials/T-2026-008-scrapling/venv"
sp = os.path.join(SCRAPLING_VENV, "lib", f"python{sys.version_info.major}.{sys.version_info.minor}", "site-packages")
if os.path.exists(sp) and sp not in sys.path:
    sys.path.insert(0, sp)

from engines.scrapling import ScraplingEngine

engine = ScraplingEngine()

HORSES = [
    (427416, "Prudentia"),
    (428364, "FirstGear"),
]

output_dir = "/tmp/evo_racing_data"
os.makedirs(output_dir, exist_ok=True)

for loveracing_id, name in HORSES:
    url = f"https://loveracing.nz/Common/SystemTemplates/Modal/EntryDetail.aspx?HorseID={loveracing_id}&DisplayContext=Modal01"
    print(f"Fetching {name} ({loveracing_id})...")
    html = engine.fetch(url)
    path = os.path.join(output_dir, f"{name}_{loveracing_id}_race_history.html")
    with open(path, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"  Saved {len(html)} chars to {path}")

print(f"\n✅ Both samples saved to {output_dir}/")
