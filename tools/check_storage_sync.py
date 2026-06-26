#!/usr/bin/env python3
"""
check_storage_sync.py — Validates the local-first storage contract.

Checks:
1. Slug sync — _assets/horses/ matches 01_evolution/horses/
2. No orphans — every slug in one surface exists in the other
3. Microchip consistency — frontmatter == table == pedigree.json == race-record.json == HORSES.csv
4. HORSES.csv sync — every horse folder has a row, and vice versa
5. Folder structure — each _assets/horses/{slug}/ has expected subfolders
6. Slug format — kebab-case or registered name (no spaces, no mixed case)
7. Website slug consistency — stables.json IDs match canonical slug list
8. No stale microchips — grep "985141" returns zero
9. JSON horse_slug consistency — horse_slug fields match folder slug
10. No stale slugs — grep "hotta-than-a-fantasy" returns zero

Usage:
    python tools/check_storage_sync.py
    python tools/check_storage_sync.py --verbose
"""

import csv
import json
import os
import re
import sys
from pathlib import Path

# ─── Paths ──────────────────────────────────────────────────────

WORKSPACE = Path(__file__).resolve().parent.parent.parent  # /home/evo/evo_01
EVOLUTION = Path(__file__).resolve().parent.parent          # /home/evo/evo_01/01_evolution
ASSETS = WORKSPACE / "_assets"
WEBSITE = WORKSPACE / "02_website"

HORSES_REPO = EVOLUTION / "horses"
HORSES_ASSETS = ASSETS / "horses"
HORSES_CSV = HORSES_ASSETS / "HORSES.csv"
STABLES_JSON = WEBSITE / "src" / "dna" / "content" / "stables.json"

EXCLUDE_DIRS = {".git", "__pycache__", ".pytest_cache", "node_modules", "_gdrive-imports", "_unidentified", ".next", ".venv", "venv"}
EXCLUDE_FILES = {"README.md", "HORSES.csv", ".gitkeep", "tsconfig.tsbuildinfo"}
EXPECTED_SUBFOLDERS = {"images", "videos", "transcripts", "documents", "investor-updates"}

# ─── Helpers ────────────────────────────────────────────────────

def parse_frontmatter(filepath: Path) -> dict:
    """Parse YAML frontmatter from a markdown file (bounded regex)."""
    try:
        text = filepath.read_text(encoding="utf-8")
    except Exception:
        return {}

    # Find first --- block
    lines = text.split("\n")
    if not lines or lines[0].strip() != "---":
        return {}

    fm = {}
    in_fm = True
    for line in lines[1:]:
        if line.strip() == "---":
            break
        if ":" in line:
            key, _, value = line.partition(":")
            key = key.strip()
            value = value.strip()
            # Strip quotes
            if value.startswith('"') and value.endswith('"'):
                value = value[1:-1]
            elif value.startswith("'") and value.endswith("'"):
                value = value[1:-1]
            # Handle list values [a, b, c]
            if value.startswith("[") and value.endswith("]"):
                value = [v.strip().strip('"').strip("'") for v in value[1:-1].split(",") if v.strip()]
            fm[key] = value
    return fm


def get_horse_dirs(path: Path) -> set:
    """Get horse slug directories, excluding special folders."""
    if not path.exists():
        return set()
    return {
        d.name for d in path.iterdir()
        if d.is_dir() and d.name not in EXCLUDE_DIRS and not d.name.startswith(".")
    }


def load_horses_csv() -> dict:
    """Load HORSES.csv as {slug: row_dict}."""
    if not HORSES_CSV.exists():
        return {}
    horses = {}
    with open(HORSES_CSV, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            slug = row.get("horse_slug", "").strip()
            if slug:
                horses[slug] = row
    return horses


def grep_pattern(directory: Path, pattern: str, exclude_dirs: set = None) -> list:
    """Search for a pattern in files under directory. Returns list of (filepath, line)."""
    results = []
    exclude = exclude_dirs or EXCLUDE_DIRS
    for root, dirs, files in os.walk(directory):
        dirs[:] = [d for d in dirs if d not in exclude]
        for fname in files:
            if fname in EXCLUDE_FILES:
                continue
            fpath = Path(root) / fname
            try:
                text = fpath.read_text(encoding="utf-8", errors="ignore")
                for i, line in enumerate(text.split("\n"), 1):
                    if pattern in line:
                        results.append((str(fpath.relative_to(WORKSPACE)), i, line.strip()[:120]))
            except Exception:
                pass
    return results


# ─── Checks ─────────────────────────────────────────────────────

class Report:
    def __init__(self):
        self.passed = []
        self.failed = []
        self.warnings = []

    def ok(self, check: str):
        self.passed.append(check)

    def fail(self, check: str, detail: str):
        self.failed.append((check, detail))

    def warn(self, check: str, detail: str):
        self.warnings.append((check, detail))

    def exit_code(self):
        return 0 if not self.failed else 1

    def print(self, verbose=False):
        print(f"\n{'='*60}")
        print(f"Storage Sync Validation — {len(self.passed)} passed, {len(self.failed)} failed, {len(self.warnings)} warnings")
        print(f"{'='*60}\n")

        if self.failed:
            print("🔴 FAILURES:")
            for check, detail in self.failed:
                print(f"  ❌ {check}")
                if verbose:
                    print(f"     {detail}")
            print()

        if self.warnings:
            print("🟡 WARNINGS:")
            for check, detail in self.warnings:
                print(f"  ⚠️  {check}")
                if verbose:
                    print(f"     {detail}")
            print()

        if self.passed:
            print("✅ PASSED:")
            for check in self.passed:
                print(f"  ✓ {check}")
            print()

        print(f"Result: {'PASS' if not self.failed else 'FAIL'} (exit {self.exit_code()})")


def run_checks(verbose=False) -> Report:
    r = Report()

    # 1. Slug sync
    repo_slugs = get_horse_dirs(HORSES_REPO)
    asset_slugs = get_horse_dirs(HORSES_ASSETS)

    if repo_slugs == asset_slugs:
        r.ok(f"Slug sync: {len(repo_slugs)} horses match between both surfaces")
    else:
        only_repo = repo_slugs - asset_slugs
        only_assets = asset_slugs - repo_slugs
        detail = f"repo only: {only_repo}, assets only: {only_assets}"
        r.fail("Slug sync: folder lists don't match", detail)

    # 2. No orphans (covered by check 1, but explicit)
    for slug in repo_slugs | asset_slugs:
        if slug not in repo_slugs:
            r.fail(f"No orphans: {slug} missing from knowledge repo", "")
        elif slug not in asset_slugs:
            r.fail(f"No orphans: {slug} missing from asset vault", "")

    # 3. Microchip consistency
    csv_data = load_horses_csv()
    for slug in sorted(repo_slugs):
        profile = HORSES_REPO / slug / "profile.md"
        pedigree = HORSES_REPO / slug / "pedigree.json"
        race_record = HORSES_REPO / slug / "race-record.json"

        if not profile.exists():
            r.fail(f"Microchip: {slug}/profile.md missing", "")
            continue

        fm = parse_frontmatter(profile)
        fm_microchip = fm.get("microchip", "")
        status = fm.get("status", "")

        # Skip coming-soon horses for microchip checks
        if status == "coming-soon" or not fm_microchip:
            r.ok(f"Microchip: {slug} exempt (status={status}, microchip empty)")
            continue

        # Check table microchip in profile.md
        try:
            text = profile.read_text(encoding="utf-8")
            table_match = re.search(r"\|\s*Microchip\s*\|\s*(\d+)\s*\|", text)
            table_microchip = table_match.group(1) if table_match else ""
        except Exception:
            table_microchip = ""

        if table_microchip and table_microchip != fm_microchip:
            r.fail(f"Microchip: {slug} table ({table_microchip}) != frontmatter ({fm_microchip})", "")
        else:
            r.ok(f"Microchip: {slug} table matches frontmatter")

        # Check pedigree.json
        if pedigree.exists():
            try:
                pdata = json.loads(pedigree.read_text(encoding="utf-8"))
                p_microchip = pdata.get("microchip", "")
                if p_microchip != fm_microchip:
                    r.fail(f"Microchip: {slug} pedigree.json ({p_microchip}) != frontmatter ({fm_microchip})", "")
                else:
                    r.ok(f"Microchip: {slug} pedigree.json matches frontmatter")
            except Exception as e:
                r.fail(f"Microchip: {slug} pedigree.json parse error: {e}", "")
        else:
            r.warn(f"Microchip: {slug} pedigree.json missing", "")

        # Check race-record.json
        if race_record.exists():
            try:
                rdata = json.loads(race_record.read_text(encoding="utf-8"))
                r_microchip = rdata.get("microchip", "")
                if r_microchip != fm_microchip:
                    r.fail(f"Microchip: {slug} race-record.json ({r_microchip}) != frontmatter ({fm_microchip})", "")
                else:
                    r.ok(f"Microchip: {slug} race-record.json matches frontmatter")
            except Exception as e:
                r.fail(f"Microchip: {slug} race-record.json parse error: {e}", "")
        else:
            r.warn(f"Microchip: {slug} race-record.json missing", "")

        # Check HORSES.csv
        if slug in csv_data:
            csv_microchip = csv_data[slug].get("microchip", "").strip()
            if csv_microchip and csv_microchip != fm_microchip:
                r.fail(f"Microchip: {slug} HORSES.csv ({csv_microchip}) != frontmatter ({fm_microchip})", "")
            elif csv_microchip:
                r.ok(f"Microchip: {slug} HORSES.csv matches frontmatter")
        else:
            r.fail(f"Microchip: {slug} missing from HORSES.csv", "")

    # 4. HORSES.csv sync
    csv_slugs = set(csv_data.keys())
    for slug in repo_slugs - csv_slugs:
        r.fail(f"HORSES.csv sync: {slug} in folders but not in HORSES.csv", "")
    for slug in csv_slugs - repo_slugs:
        r.fail(f"HORSES.csv sync: {slug} in HORSES.csv but no folder", "")
    if repo_slugs == csv_slugs and csv_slugs:
        r.ok(f"HORSES.csv sync: all {len(csv_slugs)} horses have CSV entries")

    # 5. Folder structure
    for slug in sorted(asset_slugs):
        horse_dir = HORSES_ASSETS / slug
        actual = {d.name for d in horse_dir.iterdir() if d.is_dir()}
        missing = EXPECTED_SUBFOLDERS - actual
        if missing:
            r.fail(f"Folder structure: {slug} missing subfolders: {missing}", "")
        else:
            r.ok(f"Folder structure: {slug} has all {len(EXPECTED_SUBFOLDERS)} subfolders")

    # 6. Slug format (no spaces, no uppercase)
    for slug in sorted(repo_slugs | asset_slugs):
        if " " in slug:
            r.fail(f"Slug format: '{slug}' contains spaces", "")
        elif slug != slug.lower():
            r.fail(f"Slug format: '{slug}' contains uppercase", "")
        else:
            r.ok(f"Slug format: {slug}")

    # 7. Website slug consistency
    if STABLES_JSON.exists():
        try:
            sj = json.loads(STABLES_JSON.read_text(encoding="utf-8"))
            # stables.json is a list of horse objects with "id" field
            if isinstance(sj, list):
                web_slugs = {h.get("id", "") for h in sj if isinstance(h, dict)}
            elif isinstance(sj, dict):
                web_slugs = {v.get("id", "") for v in sj.values() if isinstance(v, dict)}
            else:
                web_slugs = set()

            for slug in repo_slugs:
                if slug not in web_slugs:
                    r.warn(f"Website slug: {slug} not found in stables.json", "")
                else:
                    r.ok(f"Website slug: {slug} found in stables.json")
        except Exception as e:
            r.warn(f"Website slug: could not parse stables.json: {e}", "")
    else:
        r.warn("Website slug: stables.json not found", "")

    # 8. No stale microchips (985141)
    stale_hits = []
    for search_dir in [EVOLUTION, ASSETS, WEBSITE]:
        if search_dir.exists():
            hits = grep_pattern(search_dir, "985141")
            # Filter out archive, .git, and this script itself
            hits = [(f, l, t) for f, l, t in hits if "docs/archive/" not in f and "docs/plans/" not in f and "check_storage_sync" not in f]
            stale_hits.extend(hits)

    if stale_hits:
        detail = "\n     ".join(f"{f}:{l} → {t}" for f, l, t in stale_hits[:10])
        r.fail(f"No stale microchips: {len(stale_hits)} files contain '985141'", detail)
    else:
        r.ok("No stale microchips: '985141' not found anywhere")

    # 9. JSON horse_slug consistency
    for slug in sorted(repo_slugs):
        for json_file in [HORSES_REPO / slug / "pedigree.json", HORSES_REPO / slug / "race-record.json"]:
            if json_file.exists():
                try:
                    data = json.loads(json_file.read_text(encoding="utf-8"))
                    json_slug = data.get("horse_slug", "")
                    if json_slug and json_slug != slug:
                        r.fail(f"JSON horse_slug: {json_file.name} has '{json_slug}' != folder '{slug}'", "")
                    elif json_slug:
                        r.ok(f"JSON horse_slug: {slug}/{json_file.name} matches folder")
                except Exception:
                    pass

    # Check leases
    leases_dir = EVOLUTION / "leases"
    if leases_dir.exists():
        for lf in leases_dir.glob("*.json"):
            try:
                data = json.loads(lf.read_text(encoding="utf-8"))
                json_slug = data.get("horse_slug", "")
                if json_slug and json_slug not in repo_slugs:
                    r.fail(f"JSON horse_slug: leases/{lf.name} has '{json_slug}' not in horse folders", "")
            except Exception:
                pass

    # 10. No stale slugs
    stale_slug_hits = []
    for search_dir in [EVOLUTION, ASSETS, WEBSITE]:
        if search_dir.exists():
            hits = grep_pattern(search_dir, "hotta-than-a-fantasy")
            # Filter out docs/plans (plan doc references old slug in context) and CONVENTIONS (same)
            hits = [(f, l, t) for f, l, t in hits if "docs/plans/" not in f and "check_storage_sync" not in f and "CONVENTIONS.md" not in f]
            stale_slug_hits.extend(hits)

    if stale_slug_hits:
        detail = "\n     ".join(f"{f}:{l} → {t}" for f, l, t in stale_slug_hits[:10])
        r.fail(f"No stale slugs: {len(stale_slug_hits)} files contain 'hotta-than-a-fantasy'", detail)
    else:
        r.ok("No stale slugs: 'hotta-than-a-fantasy' not found anywhere")

    return r


# ─── Main ───────────────────────────────────────────────────────

if __name__ == "__main__":
    verbose = "--verbose" in sys.argv or "-v" in sys.argv
    report = run_checks(verbose=verbose)
    report.print(verbose=verbose)
    sys.exit(report.exit_code())