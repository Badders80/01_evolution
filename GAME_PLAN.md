# Evolution — Game Plan

**Status:** 🟢 Phase 1 — Building MVP
**Created:** 2026-05-19
**Last Updated:** 2026-05-20

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

## Related Documents

- **Current status:** [`docs/PROGRESS.md`](docs/PROGRESS.md) — Live build tracker
- **Overview:** [`docs/BUILD_SUMMARY.md`](docs/BUILD_SUMMARY.md) — High-level summary
- **Blockers:** [`BLOCKERS.md`](BLOCKERS.md) — Resolved issues + credentials
- **Laws:** [`AGENTS.md`](AGENTS.md) — Core architecture rules
- **Audit:** [`docs/audit/AUDIT.md`](docs/audit/AUDIT.md) — Quality assessments