#!/usr/bin/env python3
"""
sync_horses.py — Generate HORSES.csv from all profile.md frontmatter.

Scans 01_evolution/horses/*/profile.md, extracts frontmatter, and writes
_assets/horses/HORSES.csv. Makes the CSV a derived artifact, not manual.

Usage:
    python tools/sync_horses.py          # write CSV
    python tools/sync_horses.py --check   # compare without writing
"""

import csv
import os
import sys
from pathlib import Path

EVOLUTION = Path(__file__).resolve().parent.parent
HORSES_DIR = EVOLUTION / "horses"
CSV_PATH = EVOLUTION.parent / "_assets" / "horses" / "HORSES.csv"

EXCLUDE = {"README.md", "HORSES.csv", ".gitkeep"}


def parse_frontmatter(filepath: Path) -> dict:
    try:
        text = filepath.read_text(encoding="utf-8")
    except Exception:
        return {}
    lines = text.split("\n")
    if not lines or lines[0].strip() != "---":
        return {}
    fm = {}
    for line in lines[1:]:
        if line.strip() == "---":
            break
        if ":" in line:
            key, _, value = line.partition(":")
            key = key.strip()
            value = value.strip().strip('"').strip("'")
            fm[key] = value
    return fm


def collect_horses() -> list[dict]:
    horses = []
    if not HORSES_DIR.exists():
        return horses
    for d in sorted(HORSES_DIR.iterdir()):
        if not d.is_dir() or d.name.startswith(".") or d.name in EXCLUDE:
            continue
        profile = d / "profile.md"
        if not profile.exists():
            continue
        fm = parse_frontmatter(profile)
        horses.append({
            "horse_name": fm.get("name", d.name),
            "horse_slug": d.name,
            "microchip": fm.get("microchip", ""),
            "life_number": fm.get("life_number", ""),
            "loveracing_id": fm.get("loveracing_id", ""),
            "breeder": fm.get("breeder", ""),
        })
    return horses


def write_csv(horses: list[dict]):
    fields = ["horse_name", "horse_slug", "microchip", "life_number", "loveracing_id", "breeder"]
    with open(CSV_PATH, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        for h in horses:
            writer.writerow(h)
    print(f"✅ Wrote {len(horses)} horses to {CSV_PATH.relative_to(EVOLUTION.parent)}")


def check_csv(horses: list[dict]):
    existing = {}
    if CSV_PATH.exists():
        with open(CSV_PATH, newline="", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                existing[row.get("horse_slug", "")] = row

    new_slugs = {h["horse_slug"] for h in horses}
    old_slugs = set(existing.keys())

    missing = new_slugs - old_slugs
    extra = old_slugs - new_slugs

    if not missing and not extra:
        print("✅ HORSES.csv is in sync with profile.md frontmatter")
        return True
    else:
        if missing:
            print(f"🔴 In folders but not in CSV: {missing}")
        if extra:
            print(f"🔴 In CSV but no folder: {extra}")
        return False


if __name__ == "__main__":
    horses = collect_horses()
    if "--check" in sys.argv:
        ok = check_csv(horses)
        sys.exit(0 if ok else 1)
    else:
        write_csv(horses)