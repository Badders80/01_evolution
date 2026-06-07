# Racing Data Corpus — Full Plan

**Status:** 🟡 Phase 2 — Scoping locked, ready to build pilot
**Date:** 2026-06-06
**Game Plan Ref:** [`../GAME_PLAN.md`](../GAME_PLAN.md) Phase 2

---

## 1. Why This Exists

Evolution Stables' core product is digitally syndicated racehorse ownership. To structure, model, price, and advise on these products, we need historic income data (stakes / prize money) for NZ thoroughbreds. This document is the build plan for that dataset.

**Primary use cases:**
- Syndication pricing: expected return based on horse class/age/trainer
- Investor reporting: "horses like yours earned X% in their first season"
- Risk modelling: variance in earnings by distance, grade, career stage

---

## 2. Data Source

**Canonical source:** `loveracing.nz`
- Breeding page: `https://loveracing.nz/Breeding/{loveracingId}/{NameSlug}.aspx`
- Race history: Embedded in horse profile or modal entry pages
- Identifier: `loveracing_id` (integer) — universal across all horse pages

**Scrapability:** Cloudflare-gated. Requires JS-capable scraper (Webclaw Cloud or Scrapling StealthyFetcher). Direct HTTP requests return challenge page.

---

## 3. Module Architecture

### 3.1 Where It Lives

```
01_evolution/
├── api/
│   ├── ssot/           ← Existing: horse/owner/trainer/HLT CRUD
│   ├── assets/         ← Existing: image/document upload
│   ├── kyc/            ← Existing: Stripe Identity
│   ├── payments/       ← Existing: Stripe Checkout
│   ├── email-ingest/   ← Existing: transcript pipeline
│   ├── models/         ← Shared Pydantic models (__init__.py)
│   └── racing-data/    ← 🆕 NEW: race history scraping + data store
│       ├── main.py
│       ├── requirements.txt
│       ├── routes/
│       │   ├── __init__.py
│       │   ├── loveracing.py       # Trigger scrape for one horse
│       │   ├── batch.py            # Batch: season or list of IDs
│       │   └── results.py          # GET /racing-data/horses/{loveracing_id}
│       ├── adapters/
│       │   ├── __init__.py
│       │   └── loveracing.py       # Source-specific parsing logic
│       ├── engines/
│       │   ├── __init__.py
│       │   ├── webclaw.py          # Webclaw Cloud API harness
│       │   └── scrapling.py        # Scrapling StealthyFetcher harness
│       └── tests/
│           ├── test_loveracing_adapter.py
│           └── test_scraper_engines.py
└── dna/schemas/
    ├── horse.json        ← Existing
    ├── race.json         ← 🆕 NEW: per-race result schema
    └── scraper.json      ← 🆕 NEW: scraper job + config schema
```

### 3.2 Why `racing-data/` Is a Domain Module

**Pattern:** Same as `api/ssot/` (generic CRUD) vs `api/kyc/` (Stripe-specific). The `racing-data/` module is a **domain-specific scraper** — it owns everything about racing data acquisition and storage.

**Engine reuse:** `engines/webclaw.py` and `engines/scrapling.py` are copied here (Option B). They are generic and could also live in `03_studio` for content scraping. Each module is self-contained.

**Adapter isolation:** `adapters/loveracing.py` is source-specific. If loveracing.nz changes their HTML, only this file changes. If we add TAB NZ as a source, we add `adapters/tab_nz.py`.

**Config centralization:** API keys, rate limits, and fallback chains for racing data live in this module only.

---

## 4. Data Model

### 4.1 Race Result (per start)

```json
{
  "id": "auto-firestore-id",
  "horse_microchip": "985125000126462",
  "loveracing_id": 427416,
  "race_date": "2024-11-09",
  "venue": "Te Rapa",
  "race_name": "Maiden 1200",
  "race_class": "Maiden",
  "distance_metres": 1200,
  "field_size": 12,
  "barrier": 5,
  "jockey": "Sam Spratt",
  "trainer": "Stephen Grey",
  "finish_position": 1,
  "prize_money_nzd": 12500,
  "stake_type": "win",
  "source_url": "https://loveracing.nz/...",
  "scraped_at": "2026-06-06T12:00:00Z",
  "scraper_version": "scraper/loveracing/v0.1",
  "raw_html_checksum": "sha256:..."
}
```

**Field notes:**
- `stake_type`: `win` / `place` / `unplaced` — derived from finish position and race stakes rules
- `raw_html_checksum`: For detecting source changes / re-scrapes
- `scraper_version`: For traceability when schema evolves

### 4.2 Horse Racing Summary (computed / cached)

```json
{
  "horse_microchip": "985125000126462",
  "loveracing_id": 427416,
  "total_starts": 18,
  "total_wins": 3,
  "total_places": 7,
  "total_earnings_nzd": 84750,
  "earnings_by_age": {
    "2": 0,
    "3": 12500,
    "4": 48750,
    "5": 23500
  },
  "earnings_by_class": {
    "Maiden": 12500,
    "Open": 48750,
    "Group 3": 23500
  },
  "first_start_date": "2023-10-15",
  "last_start_date": "2025-03-22",
  "computed_at": "2026-06-06T12:00:00Z"
}
```

---

## 5. Scraper Engine Design

### 5.1 Generic Engine Interface

```python
class ScraperEngine(ABC):
    """Base class for all scraping engines."""
    
    async def fetch(self, url: str, **kwargs) -> str:
        """Return raw HTML/JSON for the given URL."""
        ...
    
    async def extract(self, url: str, prompt: str, **kwargs) -> dict:
        """LLM-guided extraction. Returns structured dict."""
        ...
```

### 5.2 Implementations

| Engine | Class | When to use | Config |
|--------|-------|-------------|--------|
| Webclaw Cloud | `WebclawEngine` | Primary for Cloudflare sites | `WEBCLAW_API_KEY` |
| Scrapling | `ScraplingEngine` | Fallback for geo-blocked sites | StealthyFetcher |
| Playwright | `PlaywrightEngine` | Last resort for JS-heavy modals | Headless browser |

### 5.3 Fallback Chain

```
1. Webclaw Cloud (/extract with antibot bypass)
2. Scrapling StealthyFetcher (local, zero API cost)
3. Playwright MCP (heaviest, always works)
```

---

## 6. Migration from Old Builds

### 6.1 What to Migrate

| Old Location | What It Is | Migrate To | How |
|--------------|-----------|------------|-----|
| `projects/SSOT_Build/data/horses/*.json` | Canonical horse JSON files | Firestore `horses` collection | Use existing `POST /horses` API — already migrated |
| `projects/Evolution_Content/scripts/scrape-webclaw.js` | Webclaw Cloud harness | `api/racing-data/engines/webclaw.py` | Port JS → Python; same API contract |
| `projects/Evolution_Content/scripts/scrape-tab-nz.py` | Scrapling harness | `api/racing-data/engines/scrapling.py` | Already Python; adapt to engine interface |
| `projects/SSOT_Build/data/templates/boilerplate.json` | Static listing text | `01_evolution/dna/` | Already copied in `dna/brand/` |

### 6.2 What NOT to Migrate

| Old Location | Why Leave It |
|--------------|-------------|
| `projects/SSOT_Build/node_modules/` | Build artifact; regenerate in `02_website` |
| `projects/SSOT_Build/.next/` | Build artifact |
| `projects/Evolution_Content/scripts/scrape-instagram.js` | Social scrapers = different domain; defer to 03_studio |
| `projects/Evolution_Content/scripts/scrape-twitter.js` | Same — social content is Step 3 |
| Old git history with secrets | BFG purge or leave behind; `evo_01` is fresh repos |

### 6.3 Cherry-Pick Migration Strategy

Don't bulk-copy directories. Instead:

1. **Identify the specific file/script** you need (e.g., `scrape-webclaw.js`)
2. **Port the logic** into the new module with the new interface
3. **Delete the old file** from `/projects/` once verified
4. **Repeat per artifact**

This prevents carrying forward anti-patterns flagged in the migration audit.

---

## 7. API Contract

### 7.1 Scrape One Horse

```
POST /racing-data/loveracing/{loveracing_id}
```

**Response:**
```json
{
  "job_id": "job-abc123",
  "status": "queued",
  "horse_microchip": "985125000126462",
  "loveracing_id": 427416,
  "estimated_races": 18
}
```

### 7.2 Get Results

```
GET /racing-data/horses/{loveracing_id}
```

**Response:**
```json
{
  "horse": { /* Horse record */ },
  "races": [ /* Array of RaceResult */ ],
  "summary": { /* HorseRacingSummary */ }
}
```

### 7.3 Batch Scrape Season

```
POST /racing-data/batch/season
```

**Body:**
```json
{
  "season": "2024/25",
  "horse_ids": [427416, 428364, ...],
  "engine_preference": "webclaw"
}
```

---

## 8. Two-Horse Pilot Detail

| Horse | loveracing_id | Test Purpose |
|-------|--------------|--------------|
| Prudentia | 427416 | Validate standard race-history scraping; mid-career mare |
| First Gear | 428364 | Validate cross-trainer consistency; likely different profile |

**Pilot success criteria:**
1. Both horses' breeding pages parse correctly into `LoveracingRef`
2. Both horses' full race histories parse into `RaceResult[]`
3. Career earnings sums are internally consistent (sum of races = total)
4. At least one race per horse has non-zero prize money
5. Scraper engine fallback chain works (Webclaw → Scrapling)

---

## 9. Build Order

| Step | Task | Owner | Output |
|------|------|-------|--------|
| 1 | Create `api/racing-data/` module scaffold | AI | Directory + `main.py` + `requirements.txt` |
| 2 | Port Webclaw engine from old build | AI | `engines/webclaw.py` |
| 3 | Port Scrapling engine from old build | AI | `engines/scrapling.py` |
| 4 | Build `race.json` schema | AI | `dna/schemas/race.json` |
| 5 | Add `RaceResult` Pydantic model | AI | `api/models/__init__.py` update |
| 6 | Build `loveracing.py` adapter | AI | Parser: HTML → `RaceResult[]` |
| 7 | Pilot scrape: Prudentia | AI | Raw data + parsed dataset |
| 8 | Pilot scrape: First Gear | AI | Raw data + parsed dataset |
| 9 | Validate totals | Human | Spot-check against published data |
| 10 | Design `races` subcollection layout | AI | Firestore schema doc |
| 11 | Build API routes (`results.py`) | AI | `GET /racing-data/horses/{id}` |
| 12 | Build batch route (`batch.py`) | AI | `POST /racing-data/batch/season` |
| 13 | Write tests | AI | `tests/` — adapter + engine validation |

---

## 10. Cross-Reference

| This Document | References |
|---------------|-----------|
| Game Plan | [`../GAME_PLAN.md`](../GAME_PLAN.md) Phase 2 |
| Architecture Rules | [`../AGENTS.md`](../AGENTS.md) |
| Build Status | [`docs/BUILD_SUMMARY.md`](docs/BUILD_SUMMARY.md) |
| Model Strategy | [`docs/MODEL_STRATEGY.md`](docs/MODEL_STRATEGY.md) |
| Old Scraper Code | `workspace/projects/Evolution_Content/scripts/scrape-webclaw.js` |
| Old TAB Scraper | `workspace/projects/Evolution_Content/scripts/scrape-tab-nz.py` |
| Old Horse Data | `workspace/projects/SSOT_Build/data/horses/*.json` |

---

**Locked:** 2026-06-06
**Next Action:** Create `api/racing-data/` module scaffold + port Webclaw engine
