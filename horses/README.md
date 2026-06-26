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

## Horses

| Slug | Name | Tokinvest Asset ID | Trainer | Status |
|------|------|-------------------|---------|--------|
| `first-gear` | First Gear | 2 | Stephen Gray (Copper Belt Lodge) | Sold Out |
| `prudentia` | Prudentia (NZ) | 10 | Lance O'Sullivan (Wexford Stables) | Sold Out |
| `hottathanafantasy` | Hotta than a fantasy (NZ) | 11 | Lance O'Sullivan (Wexford Stables) | Sold Out |
| `i-stole-a-manolo` | I Stole A Manolo (NZ) | 14 | Lance O'Sullivan & Andrew Scott (Wexford Stables) | OTC Quote |