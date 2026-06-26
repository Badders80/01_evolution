# Tools — Storage Hygiene & Automation

Scripts for validating, syncing, and managing the local-first knowledge repo.

## Scripts

| Script | Purpose | Justfile Command |
|--------|---------|-----------------|
| `check_storage_sync.py` | Validate slug sync, microchip consistency, folder structure (10 checks) | `just check-repo` |
| `sync_horses.py` | Generate `HORSES.csv` from frontmatter across all horse profiles | `just sync-horses` |
| `coverage_report.py` | Show asset coverage table per horse (images, videos, transcripts, etc.) | `just coverage` |
| `horse_dashboard.py` | Single-horse terminal dashboard (profile + assets + transcripts) | `just horse {slug}` |
| `index_horse.py` | Auto-generate transcript/update indexes for a horse | `just index-horse {slug}` |
| `migrate_updates.py` | Migrate legacy update HTML/images to per-horse folders | `just migrate-updates` |

## Validation Checks (`check_storage_sync.py`)

Runs 10 checks across the workspace:

1. **Slug sync** — `01_evolution/horses/` folder names match `_assets/horses/` folder names
2. **No orphans** — no horse folders in one surface missing from the other
3. **Microchip consistency** — frontmatter microchip matches table microchip in profile.md
4. **HORSES.csv sync** — CSV rows match frontmatter data
5. **Folder structure** — each horse has all 5 subfolders (images/, videos/, transcripts/, documents/, investor-updates/)
6. **Slug format** — lowercase, hyphens only (no underscores, no camelCase)
7. **Website slug consistency** — `02_website/src/dna/content/stables.json` horse_slug matches knowledge repo
8. **No stale microchips** — `985141...` (old placeholder) not found anywhere
9. **JSON horse_slug** — pedigree.json and race-record.json `horse_slug` field matches folder name
10. **No stale slugs** — `hotta-than-a-fantasy` (old slug) not found anywhere

### Exclusions

The validator skips build artifacts and cache directories:
- `.next/` (Next.js build output)
- `__pycache__/`
- `docs/plans/` and `docs/archive/`
- `*.tsbuildinfo`

## Pre-commit Hook

The validation script runs automatically via `.git/hooks/pre-commit`. If any check fails, the commit is blocked.

Bypass (not recommended): `git commit --no-verify`

## VS Code Tasks

Run validation from the Command Palette (`Ctrl+Shift+B`):
- **Check Repo (Storage Sync)** — full validation
- **Sync HORSES.csv** — regenerate from frontmatter
- **Asset Coverage Report** — per-horse coverage table
- **Index Horse** — generate transcript/update indexes
- **Migrate Updates (dry run)** — preview legacy migration

## Usage

```bash
# Full validation
just check-repo

# Sync HORSES.csv
just sync-horses

# Coverage report
just coverage

# Single horse dashboard
just horse prudentia

# Generate indexes
just index-horse prudentia

# Migrate legacy updates (dry run first)
just migrate-updates
just migrate-updates-run
```