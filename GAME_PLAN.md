# Evolution — Game Plan

**Status:** ✅ Sprint Zero: Complete | 🔴 Sprint One: PARKED (GCP retired) | 🟡 Post-GCP Reframe: ACTIVE
**Created:** 2026-05-19
**Last Updated:** 2026-06-24

---

## ✅ Sprint Zero: Foundation & Security — COMPLETE

**Date:** 2026-06-10
**Status:** ✅ DONE (historical — before GCP retirement)

**Deliverables:**
- ✅ Unified models (`api/core/models.py`) — single source of truth
- ✅ Test infrastructure — 128/128 passing
- ✅ Admin authentication — Firebase Auth on 20+ endpoints
- ✅ CORS restricted — allowlist, no wildcard
- ✅ Mission Control UI — sign-in/out working
- ✅ Debt sweep — zero backups, zero duplicates, clean pycache
- ✅ Stripe rules documented — `dna/conventions/STRIPE.md`

**Note:** Sprint Zero was completed while GCP was live. The auth, CORS, and admin work is now dormant (GCP retired). If GCP returns, this work is the foundation.

---

## 🔴 Sprint One: Horse Media Console + Data Sync — PARKED

**Date parked:** 2026-06-23
**Reason:** GCP billing delinquent. Firestore, GCS, and Cloud Functions are inaccessible. Sprint One depended on all three.

**Parked deliverables (not cancelled — may resume if GCP returns):**
- [ ] Add 4 horses: Prudentia, Hottathanafantasy, I-Stole-A-Manolo, First-Gear
- [ ] Fix SSOT API 403 (Cloud Functions auth for email ingest pipeline)
- [ ] Fix SQLite schema mismatch (`horse_name` column)
- [ ] Dedup transcript filenames (normalize to `transcript_{horse}_{date}.json`)
- [ ] Push all Prudentia transcripts to Firestore with real IDs
- [ ] Build horse detail media console in Mission Control UI
- [ ] Build `GET /api/horses/{microchip}/media` endpoint
- [ ] Full test suite verification

**What happened instead:** Assets were consolidated locally (427 files in `_assets/`). Horses are tracked in `_assets/horses/HORSES.csv`. The website is being reframed to operate without GCP.

See: [`docs/sprints/S01_horse_media_console.md`](docs/sprints/S01_horse_media_console.md) — original sprint plan (preserved)

---

## 🟡 Post-GCP Reframe — ACTIVE

**Date:** 2026-06-24
**Status:** IN PROGRESS
**Priority:** Replace GCP dependencies with local-first alternatives

### Goal
Reframe the website to operate as a static-first marketing site with Firebase Auth, Stripe direct, and spreadsheet-driven inventory. No GCP backend.

### Deliverables

#### Phase 1: Doc Alignment
- [x] Rewrite `02_website/AGENTS.md` — post-GCP architecture
- [x] Rewrite `02_website/HANDSHAKE.md` — local JSON data, Stripe direct
- [x] Update `01_evolution/BLOCKERS.md` — GCP retired
- [ ] Update `01_evolution/GAME_PLAN.md` — this file
- [ ] Update `02_website/BLOCKERS.md` — new post-GCP blockers

#### Phase 2: Spreadsheet Inventory + Sync
- [ ] Design Google Sheets structure (horses, HLTs, trainers, owners, holdings)
- [ ] Create sheets
- [ ] Write `scripts/sync_inventory.py` — reads sheets, writes `src/data/*.json`
- [ ] Test replay workflow: edit sheet → run script → rebuild site

#### Phase 3: Code Reframe
- [ ] Rewire `marketplace/page.tsx` — read from `src/data/hlts.json`
- [ ] Rewire `mystable/page.tsx` — read from `src/data/holdings.json`
- [x] Rewrite `api/kyc/create-session/route.ts` — direct Stripe + token verify (in 02_website)
- [x] Rewrite `api/checkout/create-session/route.ts` — direct Stripe + token verify (in 02_website)
- [x] Webhooks direct + claims/holdings write (kyc sets claims; checkout appends via sheets webapp or log)
- [ ] Dormant-ify `src/app/admin/` — keep code, remove from production nav
- [ ] Dormant-ify `src/lib/api.ts` and `src/lib/gcp-auth.ts` — keep, no active imports (some still referenced)

#### Phase 4: Deploy + Verify
- [ ] `just check` GREEN
- [ ] Vercel env vars set (`STRIPE_SECRET_KEY`, Firebase config, Stripe publishable)
- [ ] Deploy to Vercel
- [ ] Test: Firebase auth works, Stripe KYC redirects, marketplace shows listings from JSON, MyStable shows holdings from JSON

---

## 🏗️ Workspace Boundary (Updated 2026-06-24)

| Workspace | Purpose | What Lives Here |
|-----------|---------|-----------------|
| `01_evolution/` | **Backend (DORMANT)** | Cloud Functions (`api/`), Pydantic models, schemas, docs. Preserved for reference. Not deployed. |
| `02_website/` | **Frontend (ACTIVE)** | Next.js app — marketing pages, Firebase Auth, Stripe direct, local JSON data |
| `_assets/` | **Assets (ACTIVE)** | 427 consolidated files, symlinks, HORSES.csv. See `WHATS_LEFT.md` |

**Rule (updated):** `02_website` reads from local JSON (`src/data/`), not from `01_evolution/` APIs. The old data flow (`02_website → POST /api/... → 01_evolution → Firestore/GCS`) is retired. New flow: `Google Sheets → replay script → src/data/*.json → 02_website`.

---

## 🏗️ Architecture Decisions (Updated)

| Decision | Choice | Rationale | Date |
|----------|--------|-----------|------|
| ~~Database~~ | ~~Firestore~~ | ~~Real-time, cloud-accessible~~ | 2026-05-19 → **RETIRED 2026-06-23** |
| ~~API layer~~ | ~~Cloud Functions (Python)~~ | ~~Pydantic validation, GCP-native~~ | 2026-05-19 → **RETIRED 2026-06-23** |
| **Inventory data** | **Google Sheets → local JSON** | Solo-founder manageable, no infra cost, replay-on-demand | 2026-06-24 |
| **Frontend** | Next.js 16 + App Router | Team familiarity, SEO-first | 2026-05-19 |
| **Auth** | Firebase Auth (client-only) | Works without GCP backend | 2026-05-19 |
| **KYC** | Stripe Identity (direct from Next.js) | No GCP proxy needed | 2026-06-24 |
| **Payments** | Stripe Checkout (direct from Next.js) | No GCP proxy needed | 2026-06-24 |
| **Image storage** | Local `_assets/` + symlinks | 427 files consolidated, no GCS | 2026-06-22 |
| **Horse primary key** | Microchip (15 digits) | Durable, never changes, NZTR-verified | 2026-05-19 |
| **Data flow** | Sheets → script → JSON → site | Unidirectional, replay-on-demand | 2026-06-24 |

---

## Phase 2: NZ Racing Data Corpus — PARKED (GCP-dependent)

**Status:** Parked — requires Firestore for storage. The scraper code in `05_industry-data/` is preserved and can resume if GCP returns.

See original plan below (preserved for reference).

<details>
<summary>Phase 2 original plan (collapsed — GCP-dependent)</summary>

**Goal:** Build a canonical, queryable dataset of NZ thoroughbred race histories and prize-money earnings.

**Scope:**
- Scrape full race histories from `loveracing.nz` for all horses active in the last 10 years
- Structured per-race records (date, venue, class, distance, finish, prize money)
- Per-horse aggregates (career earnings, win/place rates, earnings by age/class)
- Two-horse pilot: **Prudentia (427416)** + **First Gear (428364)**
- Year-by-year iteration backward from 2024/25

**Architecture (was):**
| Decision | Choice | Rationale |
|----------|--------|-----------|
| Dataset anchor | `loveracing_id` (integer) | Universal across loveracing.nz URLs |
| Storage | Firestore subcollection `horses/{microchip}/races` | **PARKED — GCP retired** |
| Schema | JSON Schema `race.json` + Pydantic `RaceResult` | Same dual-validation pattern |
| Scraping stack | Webclaw Cloud + Scrapling StealthyFetcher | Already proven in Evolution_Content pipeline |

**If resuming:** Storage would need to move from Firestore to local JSON (same pattern as inventory) or a different database.
</details>

---

## Related Documents

- **Blockers:** [`BLOCKERS.md`](BLOCKERS.md) — Post-GCP blockers + status
- **Website:** [`../02_website/AGENTS.md`](../02_website/AGENTS.md) — Website agent rules (post-GCP)
- **Website handshake:** [`../02_website/HANDSHAKE.md`](../02_website/HANDSHAKE.md) — Data + auth contract (post-GCP)
- **Asset status:** [`../_assets/WHATS_LEFT.md`](../_assets/WHATS_LEFT.md) — Asset consolidation
- **Laws:** [`AGENTS.md`](AGENTS.md) — Core architecture rules
- **Sprint Zero (historical):** [`docs/sprints/S00_foundation_security.md`](docs/sprints/S00_foundation_security.md)
- **Sprint One (parked):** [`docs/sprints/S01_horse_media_console.md`](docs/sprints/S01_horse_media_console.md)