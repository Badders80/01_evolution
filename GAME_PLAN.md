# Evolution — Game Plan

**Status:** ✅ Sprint Zero: Complete | 🟡 Sprint One: Horse Media Console + Data Sync | 🟢 Phase 1 — Building MVP | 🟡 Phase 2 — Scoping locked
**Created:** 2026-05-19
**Last Updated:** 2026-06-10

---

## ✅ Sprint Zero: Foundation & Security — COMPLETE

**Date:** 2026-06-10  
**Status:** ✅ DONE  

**Deliverables:**
- ✅ Unified models (`api/core/models.py`) — single source of truth
- ✅ Test infrastructure — 128/128 passing
- ✅ Admin authentication — Firebase Auth on 20+ endpoints
- ✅ CORS restricted — allowlist, no wildcard
- ✅ Mission Control UI — sign-in/out working
- ✅ Debt sweep — zero backups, zero duplicates, clean pycache
- ✅ Stripe rules documented — `dna/conventions/STRIPE.md`

**See:** [`docs/sprints/S00_foundation_security.md`](docs/sprints/S00_foundation_security.md) | [`docs/sprints/SPRINT_ZERO_COMPLETE.md`](docs/sprints/SPRINT_ZERO_COMPLETE.md)

---

## 🚨 Current Sprint: Sprint One — Horse Media Console + Data Sync

**Priority:** 🔴 ACTIVE  
**Date:** 2026-06-10  
**Status:** 🟡 IN PROGRESS  

**Goal:** Add 4 Wexford horses to Mission Control, build horse detail media console, sync transcripts to Firestore.

**Key Deliverables:**
- [ ] Add 4 horses: Prudentia, Hottathanafantasy, I-Stole-A-Manolo, First-Gear
- [ ] Fix SSOT API 403 (Cloud Functions auth for email ingest pipeline)
- [ ] Fix SQLite schema mismatch (`horse_name` column)
- [ ] Dedup transcript filenames (normalize to `transcript_{horse}_{date}.json`)
- [ ] Push all Prudentia transcripts to Firestore with real IDs
- [ ] Build horse detail media console in Mission Control UI
- [ ] Build `GET /api/horses/{microchip}/media` endpoint
- [ ] Full test suite verification

**See Full Plan:** [`docs/sprints/S01_horse_media_console.md`](docs/sprints/S01_horse_media_console.md)

---

## 🏗️ Workspace Boundary (Locked 2026-05-20)

| Workspace | Purpose | What Lives Here |
|-----------|---------|-----------------|
| `01_evolution/` | **Backend only** | Cloud Functions (`api/`), Pydantic models, schemas, docs |
| `02_website/` | **Frontend only** | Next.js app — public pages + admin portal + auth |

**Rule:** `01_evolution` never contains frontend code. `02_website` never writes to Firestore directly. All data flows: `02_website` → `POST /api/...` → `01_evolution` → Firestore/GCS.

---

## 🎯 Project Overview

**Goal:** Build the minimum viable business surface for Evolution Stables — a clean public website, Stripe KYC, horse/owner intake, and an image asset centre.

**Scope:**
- Horse, owner, trainer intake with microchip-anchored identity
- HLT assembly and legal document generation (Term Sheet, PDS, SA)
- Image upload and retrieval organized by horse microchip
- Stripe Identity KYC verification for investors
- Clean public marketing pages

**Non-Goals (current phase):**
- Marketplace listings (Step 2)
- Stripe payments (Step 2)
- Content scraping pipeline (Step 3)
- Agent orchestration (Step 3)
- GST/ops processing (Step 4)
- CRM (Step 4)

---

## 🏗️ Architecture Decisions (Locked)

| Decision | Choice | Rationale | Date |
|----------|--------|-----------|------|
| Database | Firestore | Real-time, cloud-accessible, agent-friendly | 2026-05-19 |
| API layer | Cloud Functions (Python) | Pydantic validation, GCP-native | 2026-05-19 |
| Frontend | Next.js 16 + App Router + shadcn/ui | Team familiarity, SEO-first | 2026-05-19 |
| Auth | Firebase Auth + custom claims | Simple, supports admin/investor roles | 2026-05-19 |
| KYC | Stripe Identity | Already in ecosystem, NZD-compatible | 2026-05-19 |
| Image storage | Cloud Storage + Firestore metadata | CDN-ready, searchable by microchip | 2026-05-19 |
| Horse primary key | Microchip (15 digits) | Durable, never changes, NZTR-verified | 2026-05-19 |
| HLT status lifecycle | draft → reviewed → publish_ready → published | Extensible for marketplace | 2026-05-19 |
| Data flow | Unidirectional (api/ is the only writer) | Prevents bi-directional sync forever | 2026-05-19 |

---

## ✅ Phase 1 Checklist

### Checkpoint 1: Firestore + Storage
- [x] `gcloud firestore databases create` — ✅ Running
- [x] `gsutil mb gs://evolution-horse-images` — ✅ Created
- [x] `gsutil mb gs://evolution-horse-docs` — ✅ Created

### Checkpoint 2: Pydantic Models
- [x] `api/models/__init__.py` — Horse, Owner, Trainer, HLT, Asset, LoveracingRef
- [x] pytest passes for all models

### Checkpoint 3: SSOT API (Horses)
- [x] `api/ssot/routes/horses.py` — CRUD
- [x] `curl POST /horses` creates a horse in Firestore

### Checkpoint 4: SSOT API (Owners, Trainers, HLTs, Docs)
- [x] `api/ssot/routes/owners.py` — CRUD
- [x] `api/ssot/routes/trainers.py` — CRUD
- [x] `api/ssot/routes/hlts.py` — CRUD + status transitions
- [x] `api/ssot/routes/docs.py` — Generate Term Sheet, PDS, SA
- [x] All endpoints return correct responses

### Checkpoint 5: Assets API
- [x] `api/assets/routes/upload.py` — Upload to GCS + Firestore metadata
- [x] `api/assets/routes/retrieve.py` — Get by entity (microchip for horses)
- [x] `api/assets/routes/delete.py` — Remove from GCS + Firestore
- [x] Upload and retrieve cycle works

### Checkpoint 6: KYC API
- [x] `api/kyc/routes/create_session.py` — Stripe Identity session
- [x] `api/kyc/routes/webhook.py` — Stripe webhook handler
- [x] Stripe session creation works

### Checkpoint 7: Next.js App (Public Pages)
- [x] Home, About, Press pages render
- [x] DNA brand system applied

### Checkpoint 8: Next.js App (Admin + Auth) — `02_website/`
- [x] Admin pages rebuilt in `02_website/src/app/admin/` (moved from `01_evolution/app/`)
- [x] Horse intake form works
- [x] Horse list page works
- [x] Owner list + create form works
- [x] Trainer list + create form works
- [x] HLT list + create + status workflow works
- [x] Asset upload + browse works
- [x] Bulk upload with smart naming + auto-tagging works
- [x] Auth bypass for dev mode (re-enable before production)
- [ ] Firebase Auth login works with real credentials
- [ ] Google OAuth sign-in works
- [ ] Stripe KYC flow works end-to-end
- [ ] Auth guard re-enabled on `/admin/*` routes

### Checkpoint 9: Integration Test
- [ ] Create horse → create owner → create HLT → generate docs → upload image
- [ ] All tests pass

---

## 🎯 Today's Sprint (2026-05-20)

**Goal:** Make auth real. The admin portal is built and functional (auth bypassed for dev). Today we wire Firebase Auth + Stripe KYC so the login page actually works, then re-enable the auth guard.

### Morning (Done)
- [x] Fix architectural drift — delete `01_evolution/app/`, rebuild admin in `02_website/`
- [x] Auth bypass for dev mode (commented guard in `admin/layout.tsx`)
- [x] Verify all 12 admin pages render and build passes (20 pages, 0 errors)
- [x] Update docs: `PROGRESS.md`, `BUILD_SUMMARY.md`, `logs/2026-05-20.md`

### Afternoon (In Progress)
- [ ] **Firebase Auth** — Create `.env.local` with real `NEXT_PUBLIC_FIREBASE_CONFIG`
- [ ] **Email login** — Test sign-up + sign-in flow, verify token claims
- [ ] **Google OAuth** — Enable provider in Firebase Console, test one-click login
- [ ] **Stripe KYC** — Wire `STRIPE_PUBLISHABLE_KEY`, test `/auth/verify` → Stripe redirect
- [ ] **Webhook** — Verify KYC completion updates Firebase custom claims
- [ ] **Re-enable auth guard** — Uncomment the 6 lines in `admin/layout.tsx`
- [ ] **Integration test** — Full flow: register → login → KYC → access admin

### Definition of Done for Today
1. A real user can sign up with email, log in, and see the admin dashboard
2. Google OAuth button works (one-click login)
3. KYC verification redirects to Stripe and returns with verified status
4. Unauthenticated users are blocked from `/admin/*` (guard re-enabled)
5. Build passes with 0 errors

---

## 🎯 Phase 1 Definition of Done

**Phase 1 is complete when:**

1. ✅ All 9 checkpoints above are green
2. ✅ One complete E2E flow works: Create horse → create owner → create HLT → upload image
3. ✅ No TypeScript errors in production build (`npm run build` passes)
4. ✅ Cloud Functions deployed and responding (`ssot`, `assets`, `kyc`)
5. ✅ Next.js deployed (Vercel or Firebase Hosting)

**Current Status:** 8/9 checkpoints complete (~95% done)

**Remaining:** Integration test + deployment

---

## 🎯 Phase 2: NZ Racing Data Corpus (New — Locked 2026-06-06)

**Goal:** Build a canonical, queryable dataset of NZ thoroughbred race histories and prize-money earnings. This is the financial foundation for all syndication pricing, modelling, and investor returns analysis.

**Scope:**
- Scrape full race histories from `loveracing.nz` for all horses active in the last 10 years
- Structured per-race records (date, venue, class, distance, finish, prize money)
- Per-horse aggregates (career earnings, win/place rates, earnings by age/class)
- Two-horse pilot: **Prudentia (427416)** + **First Gear (428364)**
- Year-by-year iteration backward from 2024/25

**Non-Goals:**
- Full pedigree trees (sire + dam only)
- Trial/workout data (Tier 2 — documented but not scraped yet)
- Sectional times / performance analytics (Tier 2)
- Real-time / live race streaming

### Architecture Decisions (Locked)

| Decision | Choice | Rationale | Date |
|----------|--------|-----------|------|
| Dataset anchor | `loveracing_id` (integer) | Universal across loveracing.nz URLs; already in horse schema | 2026-06-06 |
| Storage | Firestore subcollection `horses/{microchip}/races` | Natural query root; no JOINs needed | 2026-06-06 |
| Schema | JSON Schema `race.json` + Pydantic `RaceResult` | Same dual-validation as horse/owner/hlt | 2026-06-06 |
| Scraping stack | Webclaw Cloud + Scrapling StealthyFetcher | Already proven in Evolution_Content pipeline | 2026-06-06 |
| Pilot scope | 2 horses, full careers | Validate scraper repeatability before batching | 2026-06-06 |
| Batch scope | Year-by-year backward from 2024/25 | Validate data quality per season before proceeding | 2026-06-06 |

### Phase 2 Checklist

#### Pilot (2 horses)
- [ ] **2.1** Scrape Prudentia breeding page → validate `loveracing_id` mapping
- [ ] **2.2** Scrape Prudentia full race history → raw HTML/JSON
- [ ] **2.3** Parse into `RaceResult` schema → structured dataset
- [ ] **2.4** Scrape First Gear breeding page + full race history
- [ ] **2.5** Parse First Gear into `RaceResult` schema
- [ ] **2.6** Validate: career totals match published stakes data (if available)
- [ ] **2.7** Write `RaceResult` Pydantic model + `race.json` JSON Schema
- [ ] **2.8** Design `horses/{microchip}/races` Firestore subcollection layout
- [ ] **2.9** API route: `GET /racing-data/horses/{loveracing_id}` → race history
- [ ] **2.10** API route: `GET /racing-data/horses/{loveracing_id}/summary` → aggregates

#### Year 1 (2024/25 season)
- [ ] **2.11** Enumerate all horse IDs with ≥1 start in 2024/25
- [ ] **2.12** Batch scrape all identified horses
- [ ] **2.13** Ingest into Firestore; validate row counts
- [ ] **2.14** Cross-check season total prize money against NZTR season summary

#### Years 2–10 (2022/23 → 2015/16)
- [ ] **2.15** Repeat 2.11–2.14 per season
- [ ] **2.16** Monitor for schema drift across seasons
- [ ] **2.17** Final dataset: ~4,000–6,000 horses, tens of thousands of race starts

### Tiered Data Boundary

**Tier 1 (Core — scrape now):**
- Per-race: date, venue, race name, class/grade, distance, field size, barrier, jockey, trainer, finish position, prize money NZD
- Per-horse: static profile + computed aggregates

**Tier 2 (Deferred — document sources only):**
- Trial/jumpout results, sectional times, stewards reports, nomination patterns, ownership changes

---

## Related Documents

- **Overview:** [`docs/BUILD_SUMMARY.md`](docs/BUILD_SUMMARY.md) — High-level summary
- **Blockers:** [`BLOCKERS.md`](BLOCKERS.md) — Resolved issues + credentials
- **Laws:** [`AGENTS.md`](AGENTS.md) — Core architecture rules
- **Audit:** [`docs/audit/AUDIT.md`](docs/audit/AUDIT.md) — Quality assessments
- **Phase 2 Detail:** [`docs/RACING_DATA_PLAN.md`](docs/RACING_DATA_PLAN.md) — Full scraper architecture, module design, migration notes