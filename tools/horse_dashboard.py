#!/usr/bin/env python3
"""
horse_dashboard.py — Single-horse dashboard.

Prints a terminal summary of a horse's profile, pedigree, race record,
and asset counts across both surfaces.

Usage:
    python tools/horse_dashboard.py prudentia
"""

import json
import sys
from pathlib import Path

EVOLUTION = Path(__file__).resolve().parent.parent
ASSETS = EVOLUTION.parent / "_assets" / "horses"


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
            fm[key.strip()] = value.strip().strip('"').strip("'")
    return fm


def count_files(path: Path) -> int:
    if not path.exists():
        return 0
    return sum(1 for f in path.iterdir() if f.is_file() and f.name not in {".gitkeep", "README.md"})


def main():
    if len(sys.argv) < 2:
        print("Usage: python tools/horse_dashboard.py <slug>")
        sys.exit(1)

    slug = sys.argv[1]
    horse_dir = EVOLUTION / "horses" / slug
    asset_dir = ASSETS / slug

    if not horse_dir.exists():
        print(f"❌ Horse '{slug}' not found in knowledge repo")
        sys.exit(1)

    print(f"\n{'='*60}")
    print(f"  🐴 {slug}")
    print(f"{'='*60}\n")

    # Profile
    profile = horse_dir / "profile.md"
    if profile.exists():
        fm = parse_frontmatter(profile)
        print("📋 PROFILE")
        print(f"   Name:      {fm.get('name', '?')}")
        print(f"   Microchip: {fm.get('microchip', '?')}")
        print(f"   Sire:      {fm.get('sire', '?')}")
        print(f"   Dam:       {fm.get('dam', '?')}")
        print(f"   Trainer:   {fm.get('trainer', '?')}")
        print(f"   Stable:    {fm.get('stable', '?')}")
        print(f"   Status:    {fm.get('status', '?')}")
    else:
        print("📋 PROFILE: missing")

    # Pedigree
    pedigree = horse_dir / "pedigree.json"
    if pedigree.exists():
        try:
            pdata = json.loads(pedigree.read_text())
            print(f"\n🧬 PEDIGREE")
            print(f"   Sire:    {pdata.get('sire', '?')}")
            print(f"   Dam:     {pdata.get('dam', '?')}")
            print(f"   Breeder: {pdata.get('breeder', '?')}")
        except Exception:
            print("\n🧬 PEDIGREE: parse error")
    else:
        print("\n🧬 PEDIGREE: missing")

    # Race record
    race = horse_dir / "race-record.json"
    if race.exists():
        try:
            rdata = json.loads(race.read_text())
            starts = rdata.get("starts", [])
            print(f"\n🏁 RACE RECORD ({len(starts)} starts)")
            for s in starts[:5]:
                print(f"   {s.get('date', '?')} | {s.get('venue', '?')} | {s.get('result', '?')}")
            if len(starts) > 5:
                print(f"   ... and {len(starts) - 5} more")
        except Exception:
            print("\n🏁 RACE RECORD: parse error")
    else:
        print("\n🏁 RACE RECORD: missing")

    # Assets
    print(f"\n📦 ASSETS (_assets/horses/{slug}/)")
    for cat in ["images", "videos", "transcripts", "documents", "investor-updates"]:
        count = count_files(asset_dir / cat)
        print(f"   {cat:<20} {count:>3} files")

    # Knowledge repo files
    print(f"\n📄 KNOWLEDGE REPO (01_evolution/horses/{slug}/)")
    for f in sorted(horse_dir.iterdir()):
        if f.is_file():
            print(f"   {f.name}")

    print()


if __name__ == "__main__":
    main()