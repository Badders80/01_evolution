# Horse Content Repository

**Purpose:** Canonical source material for every horse in the Evolution Stables roster. This is the authoring layer — pre-Firestore, pre-website. It holds the raw reference content and the living profile that downstream systems pull from.

---

## Structure

```
horses/
├── README.md                  ← You are here
├── first-gear/
│   ├── tokinvest-listing.md   ← Verbatim archive of tokinvest portal copy
│   ├── profile.md             ← Living profile in Evolution's voice
│   ├── pedigree.json          ← Structured pedigree data
│   └── race-record.json       ← Structured race starts & results
├── prudentia/
│   └── ...
├── hottathanafantasy/
│   └── ...
└── i-stole-a-manolo/
    └── ...
```

## File Roles

| File | Mutability | Purpose |
|------|-----------|---------|
| `tokinvest-listing.md` | **Frozen** — never edit | Verbatim clone of the tokinvest portal listing. Source URL + fetch date in frontmatter. This is the historical reference. |
| `profile.md` | **Living** — edit freely | The horse's profile in Evolution's brand voice. Starts as a lightly-edited version of the tokinvest copy, then evolves with race results, new photography, and Evolution-specific narrative. This is what the website eventually renders. |
| `pedigree.json` | **Living** — update as verified | Structured pedigree. Fields mirror `dna/schemas/horse.json` (sire, dam, breeder, family_number, etc.). |
| `race-record.json` | **Living** — update after each start | Structured race record. Each start: date, venue, race name, distance, track condition, jockey, result, margin, prizemoney. |

## How This Feeds Downstream

```
horses/{slug}/profile.md          ──→  Website narrative sections (marketplace, mystable)
horses/{slug}/pedigree.json       ──→  Firestore horse record (via SSOT API POST /horses)
horses/{slug}/race-record.json    ──→  Website race record tab + Firestore content records
_assets/horses/{slug}/images/     ──→  Website image components + GCS (via Assets API)
```

**The flow:** Author here → review → push to Firestore via API → website reads from Firestore. This repository is never read by the website at runtime. It's the source of truth for authoring, not for serving.

## Relationship to Other Layers

| Layer | Location | Role |
|-------|----------|------|
| **This repository** | `01_evolution/horses/` | Content authoring & canonical source material |
| **Asset library** | `_assets/horses/{slug}/` | Binary assets (images, PDFs, videos) |
| **Schemas** | `01_evolution/dna/schemas/` | Validation contracts for structured data |
| **API** | `01_evolution/api/ssot/` | Runtime CRUD — pushes this content to Firestore |
| **Website** | `02_website/src/` | Renders from Firestore, never reads this repo directly |

## Conventions

- **Slug naming:** Matches `_assets/horses/{slug}/` and `HORSES.csv` (e.g. `first-gear`, `prudentia`)
- **Frontmatter:** Each markdown file has YAML frontmatter with `source_url`, `fetched_at`, and `horse_slug`
- **Currency:** Tokinvest listings use AED. Profiles and structured data use NZD where applicable.
- **Voice:** `profile.md` follows `dna/brand/VOICE_SYSTEM.md` — professional, concise, investor-focused. Drop all tokinvest-specific regulatory language (VARA, DMCC, PDS references).

---

## loveracing.nz — identity & performance (read this first)

**Any question about starts, stakes, jockey, track conditions, or official results → start here.**

NZTR publishes every registered thoroughbred on [loveracing.nz](https://loveracing.nz). We anchor each horse to its **15-digit microchip** (never changes) and enrich from loveracing.

### Two URLs per horse

| URL type | What it holds | Pattern |
|----------|---------------|---------|
| **Stud Book** (`breeding_url` / `source_url` in `pedigree.json`) | Pedigree, brands, breeder, life number, microchip | `https://loveracing.nz/Breeding/{HorseID}/{NameSlug}.aspx` |
| **Performance profile** (`performance_profile_url`) | Career starts, stakes, jockey, track/going, ratings — updates over the horse's career | `https://loveracing.nz/Common/SystemTemplates/Modal/EntryDetail.aspx?DisplayContext=Modal&HorseID={HorseID}` |

`HorseID` = `loveracing_id` (integer). Optional query params (`JockeyID`, `TrackID`, …) on a shared link point at one race entry only — **do not store those** as the canonical performance URL. HorseID alone is enough.

### ID derivation

```
life_number  NZ00427416
loveracing_id     427416   ← strip "NZ00" prefix from life number
```

Same rule for every NZTR horse. Example: `NZ00452052` → `452052` (Hottathanafantasy).

### Where we store it (lookup order)

| Question | Look here first |
|----------|-----------------|
| Official starts / stakes / jockey / track | `horses/{slug}/race-record.json` → if stale, re-scrape **performance profile** URL from `pedigree.json` |
| Pedigree, microchip, life number, brands | `horses/{slug}/pedigree.json` |
| Human-readable links | `horses/{slug}/profile.md` → **Official records** table |
| Runtime / Firestore | `01_evolution/api/scripts/seed_canonical_entities.py` fields `breeding_url`, `performance_profile_url` |
| Website inventory | `02_website/scripts/sheet_templates/horses.csv` columns `life_number`, `loveracing_id` |

### Required JSON fields (named, NZTR-registered horses)

**`pedigree.json`:** `microchip`, `life_number`, `loveracing_id`, `source_url` (Stud Book), `performance_profile_url`

**`race-record.json`:** `loveracing_id`, `performance_profile_url`, `starts[]` (one object per official start), totals, `source: "loveracing_nz"` once verified

### Unraced vs raced

| Status | `race-record.json` | `performance_profile_url` in pedigree |
|--------|-------------------|--------------------------------------|
| **Unraced** (Hottathanafantasy, I Stole a Manolo) | `starts: []`, `total_starts: 0`. `source` may be `tokinvest_portal` until first start. Performance URL still set — loveracing page exists, just empty. | ✓ present |
| **Raced** (Prudentia, First Gear) | `starts[]` populated from loveracing; `source: "loveracing_nz"`, `verified: true` | ✓ present |
| **Pending** (Almanzor x Night Danza — unnamed) | No microchip / `loveracing_id` yet. `source: "baxltd.com"`. | Add after NZTR registration |

### When a horse gets its first start

1. Open performance profile URL — confirm starts appear on loveracing.
2. Update `race-record.json`: copy starts, totals, set `source: "loveracing_nz"`, `verified: true`, `verified_at`.
3. Update `profile.md` narrative if needed.
4. Push to Firestore via SSOT API when website/runtime needs it.

### When a pending horse is named (Almanzor path)

1. Find Stud Book page on loveracing.nz → extract `microchip`, `life_number`, `loveracing_id`, name slug.
2. Fill `pedigree.json` (all fields + both URLs).
3. Replace `race-record.json` stub with loveracing-sourced record (likely still `starts: []` if pre-debut).
4. Add **Official records** block to `profile.md`.
5. Add row to `horses.csv` / seed scripts.

---

## Horses

| Slug | Name | Tokinvest Asset ID | Trainer | Status |
|------|------|-------------------|---------|--------|
| `first-gear` | First Gear | 2 | Stephen Gray (Copper Belt Lodge) | Sold Out |
| `prudentia` | Prudentia (NZ) | 10 | Lance O'Sullivan (Wexford Stables) | Sold Out |
| `hottathanafantasy` | Hottathanafantasy (NZ) | 11 | Lance O'Sullivan (Wexford Stables) | Sold Out |
| `i-stole-a-manolo` | I Stole A Manolo (NZ) | 14 | Lance O'Sullivan & Andrew Scott (Wexford Stables) | OTC Quote |
| `almanzor-x-night-danza` | Almanzor x Night Danza (unnamed) | — | Logan Racing | Coming Soon |
| `turn-me-loose-x-yearn` | Turn Me Loose x Yearn (unnamed) | — | Stephen Gray (Copper Belt Lodge) | Coming Soon |

**Racing status:** Prudentia + First Gear — raced. Hottathanafantasy + I Stole a Manolo — registered on loveracing, unraced. Turn Me Loose x Yearn — registered on loveracing, unraced (in training with Stephen Gray). Almanzor x Night Danza — not yet on loveracing (unnamed).