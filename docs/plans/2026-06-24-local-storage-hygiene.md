# Plan: Local-First Storage Hygiene & Conventions

**Date:** 2026-06-24
**Status:** Draft v3 — stress-tested twice against nemotron-3-ultra + deepseek-v4-pro
**Scope:** Slug standardization, microchip verification, legacy updates migration, convention docs, validation script

---

## Context

The project has moved away from Firestore/GCS as the primary backend to a local-first setup (solo founder, cloud overhead too high). Two surfaces hold horse data:

- `01_evolution/horses/{slug}/` — text content (profiles, pedigrees, race records, transcript indices)
- `_assets/horses/{slug}/` — binary assets (images, videos, PDFs, transcripts, investor updates)

These are **separate by design** (text vs binary, authoring vs storage) but lack an enforced contract. Current issues:

1. Slug mismatch: `hotta-than-a-fantasy` (knowledge repo) vs `hottathanafantasy` (assets + website)
2. Microchip mismatch: frontmatter microchip ≠ table microchip in all 4 named horses
3. Legacy `_assets/updates/` folder has unsorted HTML/images that belong in per-horse folders
4. Old `Evolution_Platform/public/updates/` has 58 files (34 HTML, 23 images, 1 TXT) never migrated
5. No written conventions for the local-first storage model
6. No validation script to enforce the contract
7. `02_website/src/dna/content/stables.json` has old slug + wrong microchips + wrong sire/dam/trainer data
8. `_assets/gcs_pull.py` uses wrong microchips as keys + old slug in NAME_MAP
9. `almanzorxnightdanza` missing from `HORSES.csv`
10. Hardcoded SQLite/NDJSON paths in email ingest pipeline point outside the workspace

### Git topology (critical context)

The workspace is **not a single git repo**. It contains multiple independent repos:

| Folder | Git status | Notes |
|--------|-----------|-------|
| `/home/evo/evo_01` | Parent repo | Tracks `_assets/` (binary files gitignored, only .gitkeep + HORSES.csv tracked) |
| `01_evolution/` | **Git submodule** | Separate repo (`github.com/Badders80/01_evolution.git`). Renames need `git mv` inside the submodule for tracked files, then update parent repo pointer. |
| `02_website/` | Separate repo | `stables.json` changes need a separate commit here |
| `03_studio/` | Separate repo | Not affected by this plan |
| `_sandbox/Evolution-3.1/` | Separate repo | Already uses `hottathanafantasy` correctly — no changes needed |

**Both `horses/` and `hlts/` in `01_evolution/` are untracked** — `git status` shows `?? horses/` and `?? hlts/`. Filesystem `mv` is fine for all renames. No `git mv` needed.

### Microchip evidence summary

The `985125...` values are confirmed correct by **8+ sources**:
- `HORSES.csv` (all 4 horses)
- `01_evolution/api/admin/seed_data.py`
- `01_evolution/api/scripts/seed_canonical_entities.py`
- `01_evolution/api/scripts/seed_wexford_horses.py`
- `01_evolution/api/scripts/seed_admin_db.py`
- SQLite `ssot_local.db` horses table (with matching loveracing_ids)
- `01_evolution/horses/{slug}/pedigree.json` (all 4 horses)
- `01_evolution/horses/{slug}/race-record.json` (all 4 horses)
- `05_industry-data/tests/test_loveracing_adapter.py` (Prudentia microchip extracted from loveracing.nz HTML)
- `01_evolution/docs/BUILD_SUMMARY.md` (explicitly states microchip from loveracing.nz)

The `985141...` values appear **only** in:
- `profile.md` table rows (the bug)
- `02_website/src/dna/content/stables.json` (wrong data throughout)
- `_assets/gcs_pull.py` `HORSE_MAP` (outdated mapping)

The `9820001234567XX` values in marketplace `page.tsx` files are **placeholder/mock data** for UI development — out of scope, but documented in conventions.

---

## Phase 1: Slug Standardization

**Goal:** One canonical slug per horse, identical across both surfaces and the website.

### Decision

Use `hottathanafantasy` (no hyphens) — matches the registered name on [loveracing.nz](https://loveracing.nz/Breeding/452052/Hottathanafantasy-NZ-2023.aspx), the SQLite DB, the website marketplace code, and `_assets/horses/`. The knowledge repo is the one that's wrong.

### Steps

1. **Rename knowledge repo folder** (filesystem rename — `horses/` is untracked in the submodule):
   - `mv 01_evolution/horses/hotta-than-a-fantasy/ 01_evolution/horses/hottathanafantasy/`

2. **Rename HLT file** (filesystem rename — `hlts/` is also untracked):
   - `mv 01_evolution/hlts/hotta-than-a-fantasy.md 01_evolution/hlts/hottathanafantasy.md`

3. **Update HORSES.csv** (`_assets/horses/HORSES.csv`):
   - Change `hotta-than-a-fantasy` → `hottathanafantasy` in the `horse_slug` column
   - Change `Hotta Than A Fantasy` → `Hottathanafantasy` in the `horse_name` column (must match loveracing.nz registered name exactly — no spaces, no gaps)

4. **Add `almanzorxnightdanza` to HORSES.csv** (currently missing):
   - `Almanzor x Night Danza,almanzorxnightdanza,,pending,bax-bloodstock`
   - Empty microchip, no loveracing_id — pending case

5. **Update all references across the ENTIRE workspace** (not just `01_evolution/`):

   **Inside `01_evolution/` submodule — explicit file list:**
   - `horses/hottathanafantasy/profile.md` — slug in frontmatter + fix broken path `_assets/horses/hotta-than-a-fantasy/images/` → `_assets/horses/hottathanafantasy/images/`
   - `horses/hottathanafantasy/documents.md` — slug in frontmatter + fix broken path `_assets/horses/hotta-than-a-fantasy/documents/` → `_assets/horses/hottathanafantasy/documents/`
   - `horses/hottathanafantasy/tokinvest-listing.md` — `horse_slug` in frontmatter
   - `horses/hottathanafantasy/pedigree.json` — `horse_slug` field
   - `horses/hottathanafantasy/race-record.json` — `horse_slug` field
   - `hlts/hottathanafantasy.md` — slug, tags, horse fields in frontmatter
   - `horses/README.md` — structure tree + table entry
   - `people/lance-osullivan/profile.md` — `horses:` array
   - `people/andrew-scott/profile.md` — `horses:` array
   - `people/kylie-bax/profile.md` — `horses:` array
   - `people/bax-bloodstock/profile.md` — `horses:` array
   - `stables/wexford-stables/profile.md` — `horses:` array
   - `governing-bodies/nztr/profile.md` — `horses:` array
   - `pedigrees/contributer/profile.md` — `progeny:` array
   - `leases/lse-003.json` — `horse_slug` field
   - `docs/KNOWLEDGE_REPO_GAP_ANALYSIS.md` — update or archive (contains old slug + `985141` microchips in comparison table; will break Phase 2 verification if not addressed)
   - `docs/BUILD_SUMMARY.md` — check for old slug references

   **In `02_website/` (separate repo):**
   - `src/dna/content/stables.json` — change `"id": "hotta-than-a-fantasy"` → `"id": "hottathanafantasy"`, fix `tokinvestUrl` slug

   **In `_assets/` (parent repo):**
   - `gcs_pull.py` — update `NAME_MAP`: `hottathanafantasy` → `hottathanafantasy` (remove old mapping to `hotta-than-a-fantasy`)
   - `vision_classify.py` — update horse name enum if present
   - `vision_classification.json` — update entries if present
   - `DUPLICATE_REPORT.md` — update file path references (already broken, pointing to non-existent `hotta-than-a-fantasy` folder)
   - `horses/README.md` — update slug discrepancy note (remove the workaround explanation, slug is now consistent) + remove stale external tool path references (`/home/evo/workspace/tools/`)
   - `README.md` (top-level `_assets/README.md`) — remove "GCS is production source of truth" language, update folder structure from `{microchip}/` to `{slug}/`, mark GCS sync as optional/future

6. **Verify `_sandbox/Evolution-3.1/` is unaffected:**
   - Already uses `hottathanafantasy` correctly — no changes needed
   - Note: `_sandbox/Evolution-3.1/public/updates/` has a third copy of the update HTMLs — see Phase 3

### Verified — no changes needed (API seed scripts)

The following files already use the correct slug `hottathanafantasy` and correct `985125...` microchips. Do NOT modify them:
- `01_evolution/api/admin/seed_data.py` ✅
- `01_evolution/api/scripts/seed_wexford_horses.py` ✅
- `01_evolution/api/scripts/seed_canonical_entities.py` ✅
- `01_evolution/api/scripts/seed_admin_db.py` ✅
- `01_evolution/api/email-ingest/knowledge-base.json` ✅ (aliases already use "Hottathanafantasy")

### Verification

- `ls _assets/horses/` and `ls 01_evolution/horses/` produce identical slug lists (excluding README, HORSES.csv, .gitkeep, _gdrive-imports, _unidentified)
- `grep -r "hotta-than-a-fantasy" /home/evo/evo_01/` returns zero results (excluding `.git/` directories)
- `02_website/src/dna/content/stables.json` has `"id": "hottathanafantasy"`
- `HORSES.csv` has 5 rows (4 named + 1 pending)

---

## Phase 2: Microchip Verification & Fix

**Goal:** Every named horse has the correct microchip from loveracing.nz in all locations. Sire × dam horses (Almanzor x Night Danza) are exempt — empty string until registered.

### Source of truth

[loveracing.nz](https://loveracing.nz) is the SSOT for NZ-bred horse microchips. The `985125...` values are confirmed correct by 8+ sources (see evidence summary above). The SQLite `ssot_local.db` is the tiebreaker — it was seeded from loveracing.nz data and uses `985125...` with matching loveracing_ids.

**Fallback:** If loveracing.nz is unreachable during verification, proceed with `985125...` values — they are corroborated by `HORSES.csv`, `seed_data.py`, `test_loveracing_adapter.py` (which contains extracted loveracing HTML), and the SQLite DB. Mark verification as "pending live confirmation" rather than blocking.

### Current state

| Horse | Frontmatter ✅ | Table ❌ | HORSES.csv ✅ | stables.json ❌ | gcs_pull.py ❌ | Loveracing ID |
|-------|---------------|---------|--------------|-----------------|---------------|---------------|
| Prudentia | `985125000126462` | `985141004512345` | `985125000126462` | `985141004512345` | `985141004512345` | 427416 |
| First Gear | `985125000126713` | `985141004523601` | `985125000126713` | `985141004523601` | `985141004523601` | 428364 |
| I-Stole-A-Manolo | `985125000139219` | `985141004518932` | `985125000139219` | `985141004518932` | `985141004518932` | 451442 |
| Hottathanafantasy | `985125000139165` | `985141004517845` | `985125000139165` | `985141004517845` | `985141004517845` | 452052 |
| Almanzor x Night Danza | `""` (empty) | — | — (pending) | — | — | — |

### Steps

1. **Verify against loveracing.nz** (if reachable) — fetch each horse's breeding page and confirm the microchip. If unreachable, proceed with `985125...` (strong corroborating evidence).

2. **Fix the table in `profile.md`** for each horse — replace the incorrect `985141...` value with the verified `985125...` value:
   - `01_evolution/horses/prudentia/profile.md` — line ~32
   - `01_evolution/horses/first-gear/profile.md` — line ~32
   - `01_evolution/horses/i-stole-a-manolo/profile.md` — line ~32
   - `01_evolution/horses/hottathanafantasy/profile.md` — line ~32

3. **Fix `02_website/src/dna/content/stables.json`** — replace all `985141...` microchips with `985125...` values for all 4 horses.

4. **Fix `_assets/gcs_pull.py`** — update `HORSE_MAP` keys from `985141...` to `985125...` values.

5. **Fix `_taskmaster/server.py`** — update `MOCK_HORSES` array:
   - Fix First Gear microchip: `985125000215324` → `985125000126713`
   - Fix First Gear sire: `Darci Brahma` → `Derryn`
   - Fix First Gear dam: `Speedy Queen` → `A'Guin Ace`
   - Fix Prudentia dam: `Zabeel's Choice` → `Little Bit Irish`
   - Remove fabricated horse "Almanzor Pride" (doesn't exist) or replace with "Almanzor x Night Danza" (the actual pending horse with empty microchip)

6. **Update `docs/KNOWLEDGE_REPO_GAP_ANALYSIS.md`** — update comparison table to mark `985141` values as "DEPRECATED — fixed in storage hygiene plan" OR archive the file to `docs/archive/`. This file will break Phase 2 verification (`grep "985141"`) if not addressed.

7. **Verify `pedigree.json` and `race-record.json`** — these already use `985125...` for microchip (confirmed). The `horse_slug` field was updated in Phase 1. Verify both after Phase 1 rename.

8. **Almanzor x Night Danza** — leave as `""` with the existing note: "Not yet on loveracing.nz. Update with microchip, life number, brands, breeder once named and registered."

9. **Flag `stables.json` broader data quality issues** (separate follow-up, NOT in this plan — but CRITICAL severity):
   - **CRITICAL:** `stables.json` has fabricated sire/dam/trainer/colour data for ALL horses. Every horse has wrong sire, wrong dam, wrong trainer. The website is serving completely wrong pedigree data. Must be reconciled immediately after this plan.
   - Example: Prudentia sire listed as "Savabeel" (should be "Proisir"), dam as "Penny Ante" (should be "Little Bit Irish"), trainer as "Stephen Grey Racing" (should be "Wexford Stables")
   - Document as known issue in conventions: `stables.json` has fabricated/placeholder pedigree data that needs full reconciliation with knowledge repo profiles

### Verification

- For each named horse: `grep "microchip\|Microchip" 01_evolution/horses/{slug}/profile.md` — both values match
- `grep "985141" /home/evo/evo_01/` returns zero results (excluding `.git/`, `_sandbox/`, `docs/archive/`)
- `grep "microchip" 01_evolution/horses/{slug}/pedigree.json` — matches frontmatter
- `grep "microchip" 01_evolution/horses/{slug}/race-record.json` — matches frontmatter
- HORSES.csv microchip column matches frontmatter for all horses
- `02_website/src/dna/content/stables.json` microchips match frontmatter
- `_assets/gcs_pull.py` HORSE_MAP keys match frontmatter

---

## Phase 3: Legacy Updates Migration

**Goal:** Migrate all HTML updates, images, and videos from the old `Evolution_Platform/public/updates/` folder into per-horse `investor-updates/` and `images/`/`videos/` folders in `_assets/horses/{slug}/`. Also consolidate the existing `_assets/updates/` folder.

### Pre-flight

1. **Verify source path exists:** `ls /home/evo/workspace/projects/Evolution_Platform/public/updates/` — if missing, use `_sandbox/Evolution-3.1/public/updates/` as fallback source (third copy of same files).
2. **Note:** `_sandbox/Evolution-3.1/public/updates/` contains a third copy of the same 58 files. This is a stale copy — ignore for migration, do not delete (it's in a separate git repo).

### Source inventory

**Old platform folder** (`/home/evo/workspace/projects/Evolution_Platform/public/updates/`):
- 58 files total: 34 HTML, 14 PNG, 6 SVG, 3 JPG, 1 TXT
- Prudentia HTMLs: 17 files (Dec 2025 – May 2026)
- First Gear HTMLs: 9 files (Dec 2025 – March 2026)
- General/stable HTMLs: 8 files (templates, investor letters, TLDR)
- Brand assets: 14 files (logos, icons — 6 SVG + 8 PNG)
- Horse images: 5 files (Prudentia covers + Hottathanafantasy image)

**Existing `_assets/updates/`** (already in workspace):
- 10 files: 7 Prudentia HTMLs, 1 MP4, 1 JPG, 1 PNG (AB_Signiture.png)
- These are newer (May–June 2026) updates already partially organized

### Collision policy

When copying, if destination file already exists:
- Compare file sizes. If identical, skip (assume same file).
- If different sizes, flag for manual review.
- Use `cp -n` (no-clobber) as default, then check for missed files.

### File classification

#### Prudentia (→ `_assets/horses/prudentia/`)

**investor-updates/** (HTML files):
- `Prudentia-Pukekohe-01Apr2026.html`
- `Prudentia-Pukekohe-Gmail-01Apr2026.html`
- `Prudentia-TeRapa-02May2026.html`
- `Prudentia-TeRapa-02May2026-v2.html`
- `Prudentia-TeRapa-12Apr2026.html`
- `Prudentia-TeRapa-12Apr2026-v2.html`
- `Prudentia-TeRapa-17Apr2026.html`
- `Prudentia-TeRapa-17Apr2026-v2.html`
- `Prudentia-TeRapa-17Apr2026-v3.html`
- `Prudentia-TeRapa-17Apr2026-Gmail.html`
- `Prudentia-TeRapa-17Apr2026-Gmail-v1.html`
- `Prudentia-TeRapa-17Apr2026-Gmail-v2.html`
- `Prudentia-TeRapa-17Apr2026-Gmail-v2-dark.html`
- `Prudentia-TeRapa-Gmail-12Apr2026.html`
- `Prudentia-TeRapa-Gmail-12Apr2026-v2.html`
- `Prudentia_18April2026.html`
- `Prudentia-Update-12May2026.html`
- `Prudentia-Update-1May2026.txt` (text version of an update)
- `prudentia-terapa-17apr2026-redirect.html` (redirect stub — skip, but grep other HTMLs for references to it first)
- From `_assets/updates/`: `Prudentia_28May2026_email.html`, `Prudentia_Update_28May2026.html`, `Prudentia_Update_28May2026_email.html`, `prudentia_update_02june2026.html`, `prudentia_update_02june2026_email.html`, `prudentia_update_10june2026.html`, `prudentia_update_10june2026_email.html`

**images/** (horse-specific images only):
- `Prudentia Te Rapa Winner Cover.png`
- `Prudentia-OldPic.png`
- `Prudentia_18April_4k.png`
- `prudentia-x-cover.jpg`
- `prudentia_frame.jpg`
- From `_assets/updates/`: `prudentia_te_rapa_may30.jpg`

**videos/**:
- From `_assets/updates/`: `Prudentia_Update_27May2026.mp4`

#### First Gear (→ `_assets/horses/first-gear/`)

**investor-updates/** (HTML files):
- `First-Gear-Update-02Jan2026.html`
- `First-Gear-Update-03March2026.html`
- `First-Gear-Update-11Dec2025.html`
- `First-Gear-Update-12Dec2025.html`
- `First-Gear-Update-18Dec2025.html`
- `First-Gear-Update-18Dec2025-v1.html`
- `First-Gear-Update-19Dec2025.html`
- `First-Gear-Update-22Dec2025.html`
- `First-Gear-Update-31Dec2025.html`

#### Hottathanafantasy (→ `_assets/horses/hottathanafantasy/`)

**images/**:
- `HottathenImage.png` (Hottathanafantasy image — filename is a truncation/variant)
- `hottathen_frame.jpg` (Hottathanafantasy frame — NOT Prudentia)

#### Brand assets (→ `_assets/brand/`)

These are logos and icons, not horse-specific:
- `Evolution-Stables-Logo-Black.png`
- `Evolution-Stables-Logo-White.png`
- `Evolution-Stables-Logo-White.svg`
- `Evolution-Stables-Name-Logo-White.svg`
- `EvolutionStables-Mono-Black.png`
- `EvolutionStables-Mono-White.png`
- `EvolutionStables-Mono-White.svg`
- `Logo-Black.png`
- `Logo-White.png`
- `instagram-icon.png`, `instagram-icon.svg`
- `linkedin-icon.png`, `linkedin-icon.svg`
- `x-icon.png`, `x-icon.svg`
- `AB_Signiture.png` (from `_assets/updates/` — Andrew Baddeley signature)
- Skip if duplicates already exist in `_assets/brand/`

#### General/stable updates (→ keep in `_assets/updates/`)

These are stable-wide, not horse-specific. Keep in `_assets/updates/` (leave folder name as-is):
- `EvolutionStables_Update_15May2026.html`
- `TLDR_EvolutionStables_15May2026.html`
- `april-2026-investor.html`
- `investor-2026-04-13.html`

#### Skip/archive (templates and test files):
- `leemunroe-template.html` (email template, not content)
- `test-alpha.html`
- `test-wrapper.html`
- `prudentia-terapa-17apr2026-redirect.html` (redirect stub — grep other HTMLs for references first)

### Steps

1. **Copy (not move) files from old platform** — preserve the original folder as a backup until migration is verified. Use `cp -n` to avoid overwriting existing files at destinations.

2. **Organize into per-horse folders:**
   - Copy Prudentia HTMLs → `_assets/horses/prudentia/investor-updates/`
   - Copy First Gear HTMLs → `_assets/horses/first-gear/investor-updates/`
   - Copy Prudentia images → `_assets/horses/prudentia/images/`
   - Copy Hottathanafantasy images → `_assets/horses/hottathanafantasy/images/`
   - Copy Prudentia video → `_assets/horses/prudentia/videos/`
   - Copy brand assets → `_assets/brand/` (skip if duplicates already exist)

3. **Consolidate existing `_assets/updates/`:**
   - Move Prudentia HTMLs → `_assets/horses/prudentia/investor-updates/`
   - Move Prudentia MP4 → `_assets/horses/prudentia/videos/`
   - Move Prudentia JPG → `_assets/horses/prudentia/images/`
   - Move `AB_Signiture.png` → `_assets/brand/`
   - Keep stable-wide HTMLs in `_assets/updates/`

4. **Create/update index markdown files** in `01_evolution/horses/{slug}/`:
   - Update `prudentia/transcripts.md` (already exists) — add new HTML update entries AND update path reference from `_assets/updates/` → `_assets/horses/prudentia/investor-updates/`
   - Create `first-gear/investor-updates.md` — index of First Gear HTML updates with dates and brief descriptions
   - Create `hottathanafantasy/investor-updates.md` — if any updates exist (currently none beyond images)
   - For each HTML: extract date from filename, add a one-line description from the subject line or first heading

5. **Handle images embedded in HTML:**
   - HTML files reference images by relative path. After copying, these paths will break.
   - For now: note broken image paths in the index markdown. The HTML content (text) is preserved.
   - Future: update image paths inside HTMLs to point to the new `_assets/horses/{slug}/images/` location.

### Naming convention for migrated files

Keep original filenames as-is. Do not rename during migration — the filenames contain dates and context that are valuable. Future normalization can standardize naming, but migration priority is preservation.

### Note on git tracking

`_assets/horses/` binary files are **gitignored** (only `.gitkeep` and `HORSES.csv` are tracked). The migration in Phase 3 is filesystem-only — git will not track the copied files. This is by design — binary assets are not version-controlled.

### Verification

- `_assets/horses/prudentia/investor-updates/` contains all Prudentia HTMLs from both sources
- `_assets/horses/first-gear/investor-updates/` contains all First Gear HTMLs
- `_assets/horses/hottathanafantasy/images/` contains the Hottathanafantasy images
- `_assets/brand/` contains all logo/icon assets (no duplicates)
- `_assets/updates/` contains only stable-wide updates
- Old `Evolution_Platform/public/updates/` is untouched (backup)
- Each `01_evolution/horses/{slug}/` has an index markdown listing the investor updates
- File count: every file from the old folder is accounted for (copied, skipped, or left in stable-wide)

---

## Phase 4: Write Local-First Storage Conventions

**Goal:** Update `dna/conventions/CONVENTIONS.md` with the local-first storage model. Replace the cloud-first assumptions (Firestore/GCS/S3) with the actual operating mode.

### What to write

Add a new section: **Local-First Storage Model**

#### The two surfaces

| Surface | Path | Holds | Rule |
|---------|------|-------|------|
| Knowledge repo | `01_evolution/{entity}/{slug}/` | Text, JSON, markdown, code | "Would I open this in a text editor?" → yes |
| Asset vault | `_assets/{entity}/{slug}/` | Images, videos, PDFs, HTML, binaries | "Would I open this in a text editor?" → no |

#### Golden rules

1. **Same slug, both surfaces** — every horse uses the identical slug in `01_evolution/horses/{slug}/` and `_assets/horses/{slug}/`. Slug matches the registered name on loveracing.nz (e.g. `hottathanafantasy`, not `hotta-than-a-fantasy`).
2. **No orphans** — if a horse exists in one surface, it must exist in the other.
3. **Text → knowledge repo, binary → asset vault** — the boundary test: "would I open this in a text editor?"
4. **Pipeline outputs land in `_assets/`, get indexed in `01_evolution/`** — the email ingest pipeline writes transcript JSONs to `_assets/horses/{slug}/transcripts/`. A human curates the index in `01_evolution/horses/{slug}/transcripts.md`.
5. **Microchip is the durable anchor** — every named horse has a microchip from loveracing.nz in frontmatter, `pedigree.json`, and `race-record.json`. Sire × dam horses (unnamed) are exempt — empty string until registered.
6. **Cross-reference by relative path** — knowledge repo markdown references `_assets/` by relative path (`../../../_assets/horses/{slug}/`), never by absolute path.
7. **Cloud is optional, not required** — the local-first pipeline works without Firestore/GCS. Cloud sync is a future enhancement, not a prerequisite. No S3, no AWS.
8. **Humans are the writers** — in local-first mode, humans author content directly in `01_evolution/` (git-tracked). The API becomes a reader that syncs to cloud when cloud is re-enabled, not the sole writer. The old "API is the only writer" rule is suspended for local-first mode.

#### Writer model (updated)

| Mode | Writer | Storage | API role |
|------|--------|---------|----------|
| **Local-first (current)** | Humans edit `01_evolution/` directly | Local filesystem + git | Not required for content authoring |
| **Cloud (future, optional)** | API writes to Firestore | Firestore + GCS | Sole writer to cloud DB |

#### Deployment target (corrected)

| Surface | Current storage | Future cloud sync (optional) |
|---------|-----------------|-------------------------------|
| `01_evolution/` | Local filesystem, git-tracked | Firestore (if/when cloud backend re-enabled) |
| `_assets/` | Local filesystem, gitignored (binaries) | GCS (if/when cloud storage re-enabled) |

#### Pipeline paths (new)

The email ingest pipeline currently has hardcoded paths outside the workspace:

| Path | File | Issue |
|------|------|-------|
| `/home/evo/workspace/projects/Evolution_Content/data/ledger.sqlite` | `trigger_gmail.py`, `trigger_imap.py` | SQLite ledger outside workspace |
| `/home/evo/workspace/projects/Evolution_Content/data/content-index.ndjson` | `trigger_gmail.py`, `trigger_imap.py` | NDJSON catalog outside workspace |
| `/home/evo/workspace/projects/Evolution_Content/public/assets/` | `trigger_gmail.py` | Local asset fallback outside workspace |

**Convention:** In local-first mode, pipeline data should live inside the workspace. Recommended relocation:
- SQLite ledger → `01_evolution/api/email-ingest/data/ledger.sqlite`
- NDJSON catalog → `01_evolution/api/email-ingest/data/content-index.ndjson`
- Local asset fallback → `_assets/horses/{slug}/` (already the asset vault)
- Make paths configurable via environment variables with sensible defaults
- This is a **follow-up task**, not blocking the current plan

#### Entity coverage

| Entity | Knowledge repo (`01_evolution/`) | Asset vault (`_assets/`) | Dual-surface? |
|--------|----------------------------------|--------------------------|---------------|
| Horses | ✅ `horses/{slug}/` | ✅ `horses/{slug}/` | ✅ Yes |
| People | ✅ `people/{slug}/` | ❌ (add when headshots exist) | Future |
| Stables | ✅ `stables/{slug}/` | ❌ (add when facility photos exist) | Future |
| Pedigrees | ✅ `pedigrees/{slug}/` | ❌ | No (text-only) |
| Press | ✅ `press/` | ✅ `press/` | ✅ Yes (flat, not per-slug) |
| Governing bodies | ✅ `governing-bodies/{slug}/` | ❌ | No (text-only) |
| HLTs | ✅ `hlts/` | ❌ | No (text-only) |
| Leases | ✅ `leases/` | ❌ | No (JSON-only) |
| Brand | ❌ | ✅ `brand/` | No (binary-only) |
| Studio | ❌ | ✅ `studio/` | No (binary-only) |
| Partners | ❌ | ✅ `partners/` | No (binary-only) |

#### Special folders in `_assets/horses/`

| Folder | Purpose | Validation |
|--------|---------|------------|
| `_gdrive-imports/` | Google Drive import staging area | Excluded from slug sync check |
| `_unidentified/` | Assets not yet assigned to a horse | Excluded from slug sync check; clean up when assets are classified |

#### New horse checklist

When adding a horse, create both surfaces:

```
_assets/horses/{slug}/
├── images/
├── videos/
├── transcripts/
├── documents/
└── investor-updates/

01_evolution/horses/{slug}/
├── profile.md          (frontmatter with microchip, sire, dam, trainer, stable)
├── pedigree.json       (microchip must match profile.md)
├── race-record.json    (microchip must match profile.md)
├── transcripts.md      (indexes _assets transcripts — if applicable)
└── documents.md        (indexes _assets documents — if applicable)
```

Add entry to `_assets/horses/HORSES.csv` with: horse_name, horse_slug, microchip, life_number, loveracing_id, breeder. For pending horses (sire × dam, unnamed), use empty microchip and loveracing_id.

#### Placeholder data documentation (new)

The following files contain **placeholder/mock data** that should not be treated as production data:
- `02_website/src/app/marketplace/page.tsx` — microchips like `982000123456789` are UI placeholders
- `02_website/src/app/marketplace/[id]/page.tsx` — same placeholder microchips
- `02_website/src/dna/content/stables.json` — has wrong sire/dam/trainer data (flagged for separate reconciliation)

### Steps

1. Read current `CONVENTIONS.md` to find the insertion point
2. Add the "Local-First Storage Model" section after the existing "Data Conventions" section
3. Update the "Deployment Conventions" table to reflect local-first (mark cloud as "future/optional")
4. Update the "Security Conventions" — replace "API is the only writer" with the local-first writer model
5. Add pipeline paths section
6. Add special folders section
7. Add placeholder data documentation
8. Update `_assets/README.md` (top-level) — remove "GCS is production source of truth", change `{microchip}/` to `{slug}/` in folder structure, mark GCS sync as optional/future

### Verification

- `CONVENTIONS.md` contains the new section
- No references to S3, AWS, or "Asset CDN" as current infrastructure
- Firestore/GCS marked as "future/optional" where mentioned
- "API is the only writer" rule updated to reflect local-first writer model
- Pipeline paths documented with relocation recommendation

---

## Phase 5: Validation Script

**Goal:** A Python script that enforces the storage contract. Write it BEFORE execution, run it to see current failures, then run after each phase to verify fixes.

### Script: `01_evolution/tools/check_storage_sync.py`

**Checks:**

1. **Slug sync** — `ls _assets/horses/` matches `ls 01_evolution/horses/` (excluding README, HORSES.csv, .gitkeep, _gdrive-imports, _unidentified)
2. **No orphans** — every slug in one surface exists in the other
3. **Microchip consistency** — for each named horse (non-empty microchip in frontmatter):
   - `profile.md` frontmatter microchip == `profile.md` table microchip
   - `profile.md` frontmatter microchip == `pedigree.json` microchip
   - `profile.md` frontmatter microchip == `race-record.json` microchip
   - `profile.md` frontmatter microchip == `HORSES.csv` microchip
4. **HORSES.csv sync** — every horse folder has a row in HORSES.csv, and vice versa. Horses with `status: coming-soon` in frontmatter are exempt from microchip checks but must still have a HORSES.csv row.
5. **Folder structure** — each `_assets/horses/{slug}/` has the expected subfolders (images/, videos/, transcripts/, documents/, investor-updates/)
6. **Slug format** — all slugs are kebab-case or match registered name (no mixed case, no spaces)
7. **Website slug consistency** (bonus check) — `02_website/src/dna/content/stables.json` IDs match the canonical slug list
8. **No stale microchips** — `grep -r "985141" 01_evolution/ _assets/ 02_website/` returns zero results (excluding .git/, docs/archive/)
9. **JSON horse_slug consistency** — `horse_slug` fields in `pedigree.json`, `race-record.json`, and `leases/*.json` match the folder slug
10. **No stale slugs** — `grep -r "hotta-than-a-fantasy" 01_evolution/ _assets/ 02_website/` returns zero results (excluding .git/)

**Frontmatter parsing:** Use a bounded regex between the first two `---` lines to extract `microchip:` value. Handle:
- Empty values (`microchip: ""`)
- Quoted values (`microchip: "985125000126462"`)
- Unquoted values (`microchip: 985125000126462`)
- Missing frontmatter entirely (warn, don't fail)

**HORSES.csv as master:** HORSES.csv is the authoritative registry. Folder creation without a HORSES.csv entry is a validation failure. HORSES.csv entries without folders are also failures. Horses with `status: coming-soon` are exempt from microchip checks but must have a row (with empty microchip).

**Output:** Pass/fail per check, with specific file paths for any failures. Exit code 0 if all pass, 1 if any fail.

### Steps

1. Create `01_evolution/tools/` directory (if it doesn't exist)
2. Write `check_storage_sync.py`
3. Run it to verify the current state (should flag: slug mismatch, 4 microchip mismatches, missing almanzorxnightdanza in HORSES.csv, stale 985141 microchips in stables.json + gcs_pull.py + KNOWLEDGE_REPO_GAP_ANALYSIS.md, stale slug in ~15 files, JSON horse_slug mismatch)
4. After each phase, run again to verify fixes

### Verification

- Script runs without errors
- Before fixes: reports all known issues
- After fixes: all checks pass (exit code 0)

---

## Execution Order (Revised)

| Phase | Depends on | Estimated effort | Can parallelize? |
|-------|------------|-----------------|-----------------|
| 4. Write conventions | None | 25 min | — |
| 5. Validation script | None (write it to test current state) | 25 min | Yes, with Phase 4 |
| 1. Slug standardization | None | 20 min | After Phase 5 written |
| 2. Microchip fix | Phase 1 (for hottathanafantasy rename) | 35 min | After Phase 1 |
| 3. Legacy migration | Phase 1 (for correct slug folders) | 45 min | Yes, with Phase 2 |
| 6. Prevention tooling | Phases 1-5 complete | 90 min | After Phase 3 |

### Recommended sequence

1. **Phase 4** (write conventions) + **Phase 5** (write validation script) — in parallel. Document the rules and build the checker first.
2. **Run validation script** — capture current failures as a baseline.
3. **Phase 1** (slug fix) — fix slug across entire workspace. Run validation script to verify.
4. **Phase 2** (microchip fix) — fix microchips across entire workspace. Run validation script to verify.
5. **Phase 3** (legacy migration) — migrate files. Verify manually (validation script doesn't check file migration).
6. **Phase 6** (prevention tooling) — build the commands and hooks that prevent future drift.

### Git commit strategy + rollback

**Commit after each phase** — this provides a rollback point if a phase fails midway:

- **Phase 1+2 changes in `01_evolution/`** — commit inside the submodule: `cd 01_evolution && git add -A && git commit -m "fix: standardize slug + microchip data"`
- **Phase 1+2 changes in `02_website/`** — commit in the website repo: `cd 02_website && git add -A && git commit -m "fix: update stables.json slug + microchips"`
- **Phase 1+2 changes in `_assets/`** — commit in parent repo: `cd /home/evo/evo_01 && git add _assets/ && git commit -m "fix: update HORSES.csv + gcs_pull.py slug + microchips"`
- **Phase 1+2 changes in `_taskmaster/`** — commit in parent repo: `cd /home/evo/evo_01 && git add _taskmaster/ && git commit -m "fix: update server.py mock horse data"`
- **Phase 3 migration** — filesystem-only (binaries are gitignored), no commit needed except for index markdown files in `01_evolution/`
- **Phase 4 conventions** — commit inside submodule: `cd 01_evolution && git add dna/conventions/CONVENTIONS.md && git commit -m "docs: add local-first storage conventions"`
- **Phase 5 script** — commit inside submodule: `cd 01_evolution && git add tools/ && git commit -m "feat: add storage sync validation script"`
- **Phase 6 tooling** — commit inside submodule: `cd 01_evolution && git add Justfile tools/ && git commit -m "feat: add prevention tooling commands"`
- **Update parent repo submodule pointer** after `01_evolution` commits: `cd /home/evo/evo_01 && git add 01_evolution && git commit -m "chore: update 01_evolution submodule"`

**Rollback:** If a phase fails midway, `git checkout` the affected repo(s) to the last commit. Since `horses/` and `hlts/` are untracked, filesystem operations can't be rolled back via git — use `mv` to rename back if needed.

---

## Phase 6: Prevention Tooling

**Goal:** Build the tools that prevent the same drift from recurring. The plan fixes the past; this phase protects the future. Without it, the next horse addition will recreate the same slug/microchip mismatch.

### Tooling additions

All commands go in `01_evolution/Justfile`. Scripts go in `01_evolution/tools/`.

| Command | Purpose | Effort |
|--------|---------|--------|
| `just new-horse slug="name" microchip="123"` | Scaffold both surfaces (`_assets/horses/{slug}/` folders + `01_evolution/horses/{slug}/` files) + HORSES.csv entry in one shot | 20 min |
| `just check-repo` | Run `check_storage_sync.py` — the validation script from Phase 5 | 5 min |
| `just index-horse slug="prudentia"` | Auto-generate `transcripts.md` and `investor-updates.md` by scanning `_assets/horses/{slug}/` folders. Index files become generated, not hand-maintained. Add `<!-- AUTO-GENERATED -->` marker. | 30 min |
| `just sync-horses` | Generate `HORSES.csv` from all `profile.md` frontmatter. Makes CSV a derived artifact, not manual. Reports any horses in folders but missing from CSV (or vice versa). | 20 min |
| `just migrate-updates` | Scan old platform folder for files not yet in `_assets/horses/`, classify by filename pattern, copy to right per-horse folder. Makes migration repeatable. | 30 min |
| `just coverage` | Print asset coverage table per horse: images, videos, transcripts, documents, investor-updates counts. Makes gaps visible at a glance. | 20 min |
| `just horse slug="prudentia"` | Print single-horse dashboard: profile summary, pedigree, race record, asset counts, transcript list, update list. Single pane of glass per horse. | 20 min |

### Infrastructure additions

| Addition | Purpose | Effort |
|----------|---------|--------|
| Git pre-commit hook | Runs `check_storage_sync.py` before commits in `01_evolution/`. Blocks commit if validation fails. | 10 min |
| `.vscode/tasks.json` | VS Code task that runs `just check-repo` on save of any file in `01_evolution/horses/` or `_assets/horses/`. Real-time drift detection. | 10 min |
| `_assets/updates/README.md` | One-paragraph README explaining: stable-wide updates only, horse-specific updates go in `_assets/horses/{slug}/investor-updates/`. Prevents future misplacement. | 5 min |

### Priority order

1. `just new-horse` — highest leverage, prevents the exact drift this plan exists to fix
2. `just check-repo` — makes validation script discoverable
3. Git pre-commit hook — enforces contract automatically
4. `just sync-horses` — makes HORSES.csv derived, not manual
5. `just index-horse` — eliminates manual index maintenance
6. `just horse` — single pane of glass
7. `just coverage` — makes gaps visible
8. `just migrate-updates` — repeatable migration
9. `.vscode/tasks.json` — real-time feedback
10. `_assets/updates/README.md` — prevents misplacement

### Verification

- `just new-horse slug="test-horse"` creates both surfaces + HORSES.csv entry
- `just check-repo` runs without errors and passes all checks
- `just sync-horses` regenerates HORSES.csv matching frontmatter
- `just horse slug="prudentia"` prints a readable dashboard
- Pre-commit hook blocks a commit that introduces a slug mismatch

---

## What's NOT in this plan

- **CRITICAL:** `stables.json` full data reconciliation (wrong sire/dam/trainer/colour for ALL horses) — flagged as separate follow-up, must be reconciled immediately after this plan
- Marketplace `page.tsx` placeholder microchip cleanup — documented as known placeholder data
- Cloud Function deployment (deferred — local-first is the operating mode)
- Firestore sync (deferred — cloud backend on hold)
- Email ingest pipeline fixes (separate plan — see `email-ingest-next-steps.md`)
- Email ingest hardcoded path relocation (documented in conventions, execution is a follow-up)
- Transcript filename normalization (noted in email-ingest doc, not blocking)
- HTML image path fixing inside migrated HTMLs (noted as future work in Phase 3)
- `_sandbox/Evolution-3.1/` cleanup (stale copy, separate repo, leave as-is)

---

## Stress-Test Findings

### Round 1 (v1 → v2)

This plan was stress-tested against nemotron-3-ultra and deepseek-v4-pro subagents. The following issues were found and addressed:

**Blockers (fixed in v2):**
1. `stables.json` has old slug + wrong microchips — added to Phase 1 and Phase 2 scope
2. `gcs_pull.py` has wrong microchips + old slug — added to Phase 1 and Phase 2 scope
3. `01_evolution/` is a git submodule — added git topology section + commit strategy

**Warnings (fixed in v2):**
4. Slug search scope too narrow — expanded to entire workspace
5. `_sandbox/Evolution-3.1/` third copy — documented, ignored for migration
6. `almanzorxnightdanza` missing from HORSES.csv — added to Phase 1
7. Hardcoded pipeline paths — documented in Phase 4 conventions
8. "API is the only writer" obsolete — replaced with local-first writer model
9. `hottathen_frame.jpg` double-listed — fixed, only under Hottathanafantasy
10. No collision policy — added `cp -n` policy to Phase 3
11. Broken path in profile.md — added to Phase 1 fix list
12. `_assets/horses/README.md` stale note — added to Phase 1 update list
13. Validation script should run before execution — moved before Phase 1
14. Frontmatter parsing method — specified in Phase 5
15. Loveracing.nz unreachable fallback — added to Phase 2
16. `stables.json` broader data quality — flagged as separate follow-up

### Round 2 (v2 → v3)

Stress-tested again. The following issues were found and addressed:

**Blockers (fixed in v3):**
17. **Phase 6 tooling absent from document** — added Phase 6: Prevention Tooling with 10 tooling ideas
18. **`KNOWLEDGE_REPO_GAP_ANALYSIS.md` contains `985141` microchips** — added to Phase 2 fix list (update or archive)
19. **`_taskmaster/server.py` has wrong mock horse data** — added to Phase 2 fix list (wrong microchip, wrong sire/dam, fabricated horse)
20. **`hlts/` is untracked, not tracked** — fixed `git mv` → `mv` for HLT file rename

**Warnings (fixed in v3):**
21. **`documents.md` has broken `_assets/` path** — added to Phase 1 explicit file list
22. **JSON `horse_slug` fields need slug update** — added to Phase 1 explicit file list
23. **HORSES.csv display name should stay title case** — fixed, only slug column changes
24. **`_assets/README.md` top-level has stale cloud-first language** — added to Phase 4 scope
25. **`prudentia/transcripts.md` references `_assets/updates/`** — added path update to Phase 3
26. **`stables.json` severity not emphasized** — upgraded to CRITICAL in NOT-in-plan section
27. **No rollback strategy** — added commit-after-each-phase + rollback instructions
28. **Validation script doesn't check JSON `horse_slug`** — added check #9 to Phase 5
29. **No explicit file list for slug replacement** — added ~15 files to Phase 1
30. **No "verified, no changes" section for API seed scripts** — added to Phase 1
31. **`_assets/horses/README.md` has stale external tool paths** — added to Phase 1 update list