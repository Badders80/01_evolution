# Evolution — Conventions

**Version:** 1.0
**Last Updated:** 2026-05-19

---

## Naming Conventions

### Files and Folders

| Type | Convention | Example |
|------|-----------|---------|
| API routes | kebab-case | `create_session.py`, `delete_asset.py` |
| React components | PascalCase | `HorseForm.tsx`, `AssetUpload.tsx` |
| React pages | kebab-case folders | `admin/horses/new/page.tsx` |
| JSON Schemas | snake_case | `horse.json`, `owner.json` |
| Pydantic models | PascalCase classes | `HorseCreate`, `OwnerUpdate` |
| Firestore collections | plural lowercase | `horses`, `owners`, `trainers`, `hlts`, `assets` |
| GCS paths | `{entity_type}/{entity_id}/{uuid}.{ext}` | `horse/985125000126462/a1b2c3.jpg` |

### Code

| Language | Convention | Notes |
|----------|-----------|-------|
| Python | PEP 8, snake_case functions | `create_horse()`, `get_horse_by_microchip()` |
| TypeScript | camelCase functions, PascalCase types | `createHorse()`, `HorseCreate` |
| CSS | Tailwind utility classes | No custom CSS files |
| Firestore fields | snake_case | `foaling_date`, `sire_name`, `life_number` |

## API Conventions

### URL Patterns

| Entity | List | Get | Create | Update | Delete |
|--------|------|-----|--------|--------|--------|
| Horses | `GET /horses` | `GET /horses/{microchip}` | `POST /horses` | `PATCH /horses/{microchip}` | `DELETE /horses/{microchip}` |
| Owners | `GET /owners` | `GET /owners/{id}` | `POST /owners` | `PATCH /owners/{id}` | `DELETE /owners/{id}` |
| Trainers | `GET /trainers` | `GET /trainers/{id}` | `POST /trainers` | `PATCH /trainers/{id}` | `DELETE /trainers/{id}` |
| HLTs | `GET /hlts` | `GET /hlts/{id}` | `POST /hlts` | `PATCH /hlts/{id}` | `DELETE /hlts/{id}` |
| Assets | — | `GET /retrieve?entity_type=...&entity_id=...` | `POST /upload` | — | `DELETE /delete?asset_id=...` |
| KYC | — | — | `POST /create-session` | — | — |

### Response Shapes

**Success:**
```json
{
  "id": "...",
  "microchip": "985125000126462",
  ...
}
```

**List:**
```json
{
  "horses": [...],
  "count": 42
}
```

**Error:**
```json
{
  "error": "Microchip must be exactly 15 digits"
}
```

### HTTP Status Codes

| Code | Usage |
|------|-------|
| 200 | Success (get, update) |
| 201 | Created |
| 400 | Validation error |
| 404 | Not found |
| 405 | Method not allowed |
| 409 | Conflict (duplicate microchip) |

## Data Conventions

### Primary Keys

| Entity | Primary Key | Format |
|--------|------------|--------|
| Horse | `microchip` | 15 digits, queried by Firestore `where` clause |
| Owner | `id` (auto-generated) | Firestore document ID |
| Trainer | `id` (auto-generated) | Firestore document ID |
| HLT | `id` (auto-generated) | Firestore document ID |
| Asset | `id` (auto-generated) | Firestore document ID |
| User | `id` (Firebase Auth UID) | Firebase Auth UID |

### Timestamps

All entities have `created_at` and `updated_at` fields using `SERVER_TIMESTAMP`.

### Status Fields

HLT status follows a strict state machine:
```
draft → reviewed → publish_ready → published
  ↑         ↓          ↓              ↓
  └─────────┘          └──────────────┘
```

Step 1 only uses `draft` and `reviewed`.

## Local-First Storage Model

The project operates **local-first** — content is authored and stored on the local filesystem, not in cloud databases. Cloud sync (Firestore/GCS) is a future enhancement, not a prerequisite. No S3, no AWS.

### The Two Surfaces

| Surface | Path | Holds | Rule |
|---------|------|-------|------|
| Knowledge repo | `01_evolution/{entity}/{slug}/` | Text, JSON, markdown, code | "Would I open this in a text editor?" → yes |
| Asset vault | `_assets/{entity}/{slug}/` | Images, videos, PDFs, HTML, binaries | "Would I open this in a text editor?" → no |

### Golden Rules

1. **Same slug, both surfaces** — every horse uses the identical slug in `01_evolution/horses/{slug}/` and `_assets/horses/{slug}/`. Slug matches the registered name on loveracing.nz (e.g. `hottathanafantasy`, not `hotta-than-a-fantasy`).
2. **No orphans** — if a horse exists in one surface, it must exist in the other.
3. **Text → knowledge repo, binary → asset vault** — the boundary test: "would I open this in a text editor?"
4. **Pipeline outputs land in `_assets/`, get indexed in `01_evolution/`** — the email ingest pipeline writes transcript JSONs to `_assets/horses/{slug}/transcripts/`. A human curates the index in `01_evolution/horses/{slug}/transcripts.md`.
5. **Microchip is the durable anchor** — every named horse has a microchip from loveracing.nz in frontmatter, `pedigree.json`, and `race-record.json`. Sire × dam horses (unnamed) are exempt — empty string until registered.
6. **Cross-reference by relative path** — knowledge repo markdown references `_assets/` by relative path (`../../../_assets/horses/{slug}/`), never by absolute path.
7. **Cloud is optional, not required** — the local-first pipeline works without Firestore/GCS. Cloud sync is a future enhancement, not a prerequisite. No S3, no AWS.
8. **Humans are the writers** — in local-first mode, humans author content directly in `01_evolution/` (git-tracked). The API becomes a reader that syncs to cloud when cloud is re-enabled, not the sole writer. The old "API is the only writer" rule is suspended for local-first mode.

### Writer Model

| Mode | Writer | Storage | API role |
|------|--------|---------|----------|
| **Local-first (current)** | Humans edit `01_evolution/` directly | Local filesystem + git | Not required for content authoring |
| **Cloud (future, optional)** | API writes to Firestore | Firestore + GCS | Sole writer to cloud DB |

### Deployment Target

| Surface | Current storage | Future cloud sync (optional) |
|---------|-----------------|-------------------------------|
| `01_evolution/` | Local filesystem, git-tracked | Firestore (if/when cloud backend re-enabled) |
| `_assets/` | Local filesystem, gitignored (binaries) | GCS (if/when cloud storage re-enabled) |

### Pipeline Paths

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
- This is a follow-up task, not blocking.

### Entity Coverage

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

### Special Folders in `_assets/horses/`

| Folder | Purpose | Validation |
|--------|---------|------------|
| `_gdrive-imports/` | Google Drive import staging area | Excluded from slug sync check |
| `_unidentified/` | Assets not yet assigned to a horse | Excluded from slug sync check; clean up when assets are classified |

### New Horse Checklist

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

### Placeholder Data Documentation

The following files contain **placeholder/mock data** that should not be treated as production data:
- `02_website/src/app/marketplace/page.tsx` — microchips like `982000123456789` are UI placeholders
- `02_website/src/app/marketplace/[id]/page.tsx` — same placeholder microchips
- `02_website/src/dna/content/stables.json` — has wrong sire/dam/trainer data (flagged for separate reconciliation)

## Security Conventions

1. **Local-first writer model.** In local-first mode, humans author content directly in `01_evolution/` (git-tracked). The old "API is the only writer" rule is suspended. When cloud is re-enabled, the API becomes the sole writer to Firestore.
2. **Firebase Auth + custom claims.** Roles: `admin`, `investor`, `viewer`. (Required for cloud mode, not for local authoring.)
3. **Stripe Identity for KYC.** Investors must be verified before investing.
   → **Full spec:** [`dna/conventions/STRIPE.md`](STRIPE.md)
4. **Cloud Functions validate all input.** Pydantic models enforce schema. (When deployed.)
5. **GCS buckets are private.** Signed URLs for asset access. (When cloud storage re-enabled.)

## Deployment Conventions

| Component | Current (local-first) | Future (cloud, optional) | Region |
|-----------|----------------------|--------------------------|--------|
| Content storage | Local filesystem + git | Firestore | australia-southeast1 |
| Binary storage | Local filesystem (`_assets/`, gitignored) | Cloud Storage | australia-southeast1 |
| API | Not required for authoring | Cloud Functions | australia-southeast1 |
| Next.js | Vercel (or Cloud Run) | Vercel (or Cloud Run) | — |

## Git Conventions

- **Branch naming:** `feature/{description}`, `fix/{description}`
- **Commit messages:** Conventional commits (`feat:`, `fix:`, `docs:`, `chore:`)
- **PR titles:** Descriptive, reference the checkpoint number