#!/usr/bin/env python3
"""
coverage_report.py — Asset coverage per horse.

Scans _assets/horses/{slug}/ and prints a table showing
image, video, transcript, document, and update counts per horse.

Usage:
    python tools/coverage_report.py
"""

import os
from pathlib import Path

ASSETS = Path(__file__).resolve().parent.parent.parent / "_assets" / "horses"
CATEGORIES = ["images", "videos", "transcripts", "documents", "investor-updates"]
EXCLUDE = {".gitkeep", "README.md", "HORSES.csv", "_gdrive-imports", "_unidentified"}


def count_files(path: Path) -> int:
    if not path.exists():
        return 0
    return sum(1 for f in path.iterdir() if f.is_file() and f.name != ".gitkeep" and f.name != "README.md")


def main():
    if not ASSETS.exists():
        print("❌ _assets/horses/ not found")
        return

    horses = sorted(d.name for d in ASSETS.iterdir() if d.is_dir() and d.name not in EXCLUDE and not d.name.startswith("."))

    # Header
    print(f"\n{'Horse':<25} {'Images':>7} {'Videos':>7} {'Transcripts':>12} {'Documents':>10} {'Updates':>8}")
    print("-" * 75)

    for slug in horses:
        row = [slug]
        for cat in CATEGORIES:
            count = count_files(ASSETS / slug / cat)
            row.append(count)
        print(f"{row[0]:<25} {row[1]:>7} {row[2]:>7} {row[3]:>12} {row[4]:>10} {row[5]:>8}")

    print()


if __name__ == "__main__":
    main()