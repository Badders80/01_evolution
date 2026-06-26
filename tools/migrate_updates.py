#!/usr/bin/env python3
"""
migrate_updates.py — Repeatable update migration from old platform folder.

Scans the old Evolution_Platform/public/updates/ folder for files not yet
in _assets/horses/{slug}/, classifies by filename pattern, and copies to
the correct per-horse folder. Safe to run repeatedly — skips files that
already exist at destination.

Usage:
    python tools/migrate_updates.py              # migrate
    python tools/migrate_updates.py --dry-run     # preview only
"""

import os
import re
import shutil
import sys
from pathlib import Path

WORKSPACE = Path(__file__).resolve().parent.parent.parent
ASSETS = WORKSPACE / "_assets"
BRAND = ASSETS / "brand"
UPDATES = ASSETS / "updates"

# Default source (old platform)
DEFAULT_SOURCE = Path("/home/evo/workspace/projects/Evolution_Platform/public/updates")
# Fallback source (sandbox copy)
FALLBACK_SOURCE = WORKSPACE / "_sandbox" / "Evolution-3.1" / "public" / "updates"

# Classification rules: (pattern, destination_subfolder)
# Patterns are checked in order — first match wins
CLASSIFICATION = [
    # Skip patterns FIRST (before horse patterns so they take priority)
    (re.compile(r"^leemunroe-template", re.IGNORECASE), "SKIP", "SKIP"),
    (re.compile(r"^test-", re.IGNORECASE), "SKIP", "SKIP"),
    (re.compile(r"^test_wrapper", re.IGNORECASE), "SKIP", "SKIP"),
    (re.compile(r".*redirect\.html$", re.IGNORECASE), "SKIP", "SKIP"),
    # Prudentia
    (re.compile(r"^Prudentia", re.IGNORECASE), "prudentia", "investor-updates"),
    (re.compile(r"^prudentia", re.IGNORECASE), "prudentia", "investor-updates"),
    # First Gear
    (re.compile(r"^First-Gear", re.IGNORECASE), "first-gear", "investor-updates"),
    (re.compile(r"^first.gear", re.IGNORECASE), "first-gear", "investor-updates"),
    # Hottathanafantasy
    (re.compile(r"^Hottathen", re.IGNORECASE), "hottathanafantasy", "images"),
    (re.compile(r"^hottathen", re.IGNORECASE), "hottathanafantasy", "images"),
    # Brand assets
    (re.compile(r"^Evolution-Stables-Logo", re.IGNORECASE), None, "brand"),
    (re.compile(r"^Evolution-Stables-Name-Logo", re.IGNORECASE), None, "brand"),
    (re.compile(r"^EvolutionStables", re.IGNORECASE), None, "brand"),
    (re.compile(r"^Logo-", re.IGNORECASE), None, "brand"),
    (re.compile(r"^instagram-icon", re.IGNORECASE), None, "brand"),
    (re.compile(r"^linkedin-icon", re.IGNORECASE), None, "brand"),
    (re.compile(r"^x-icon", re.IGNORECASE), None, "brand"),
    (re.compile(r"^AB_Signiture", re.IGNORECASE), None, "brand"),
    # Stable-wide updates (keep in _assets/updates/)
    (re.compile(r"^EvolutionStables_Update", re.IGNORECASE), None, "updates"),
    (re.compile(r"^TLDR_EvolutionStables", re.IGNORECASE), None, "updates"),
    (re.compile(r"^april-2026-investor", re.IGNORECASE), None, "updates"),
    (re.compile(r"^investor-2026", re.IGNORECASE), None, "updates"),
]

# Prudentia images (not HTML)
PRUDENTIA_IMAGE_PATTERNS = [
    re.compile(r"^Prudentia.*\.(png|jpg|jpeg)$", re.IGNORECASE),
    re.compile(r"^prudentia.*\.(png|jpg|jpeg)$", re.IGNORECASE),
]


def classify_file(filename: str):
    """Returns (horse_slug, category) or ('SKIP', 'SKIP') or ('UNKNOWN', 'UNKNOWN')"""
    # Check Prudentia images first (before HTML classification)
    for pattern in PRUDENTIA_IMAGE_PATTERNS:
        if pattern.match(filename):
            return ("prudentia", "images")

    for pattern, horse, category in CLASSIFICATION:
        if pattern.match(filename):
            return (horse, category)

    return ("UNKNOWN", "UNKNOWN")


def find_source():
    """Find the source directory for old updates."""
    if DEFAULT_SOURCE.exists():
        return DEFAULT_SOURCE
    if FALLBACK_SOURCE.exists():
        print(f"⚠️  Default source not found, using fallback: {FALLBACK_SOURCE}")
        return FALLBACK_SOURCE
    return None


def migrate(dry_run=False):
    source = find_source()
    if not source:
        print("❌ No source directory found for old updates")
        print(f"   Checked: {DEFAULT_SOURCE}")
        print(f"   Checked: {FALLBACK_SOURCE}")
        return 1

    print(f"Source: {source}")
    print(f"Mode: {'DRY RUN' if dry_run else 'MIGRATE'}")
    print()

    files = sorted([f for f in source.iterdir() if f.is_file()])
    migrated = 0
    skipped = 0
    unknown = 0
    already_exists = 0

    for f in files:
        horse, category = classify_file(f.name)

        if horse == "SKIP":
            skipped += 1
            continue

        if horse == "UNKNOWN":
            unknown += 1
            print(f"  ❓ UNKNOWN: {f.name}")
            continue

        # Determine destination
        if category == "brand":
            dest = BRAND / f.name
        elif category == "updates":
            dest = UPDATES / f.name
        elif horse and category:
            dest = ASSETS / "horses" / horse / category / f.name
        else:
            unknown += 1
            continue

        if dest.exists():
            already_exists += 1
            continue

        if dry_run:
            print(f"  → {f.name} → {dest.relative_to(WORKSPACE)}")
            migrated += 1
        else:
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(f, dest)
            print(f"  ✅ {f.name} → {dest.relative_to(WORKSPACE)}")
            migrated += 1

    print()
    print(f"Summary: {migrated} {'would be ' if dry_run else ''}migrated, {already_exists} already exist, {skipped} skipped, {unknown} unknown")

    if unknown > 0:
        print(f"\n⚠️  {unknown} files could not be classified. Review manually.")

    return 0


if __name__ == "__main__":
    dry_run = "--dry-run" in sys.argv
    sys.exit(migrate(dry_run=dry_run))