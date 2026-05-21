# Step 1 Build Status — Live Tracker

**Date:** 2026-05-19
**Purpose:** Track what's actually been built vs what the plan specified. This is the source of truth for current state.

---

## Overall Progress: 56 / 76 files (74%)

| Layer | Planned | Built | Status |
|-------|---------|-------|--------|
| `api/models/` | 6 | 1 (combined `__init__.py`) | ✅ Complete — all models in one file |
| `api/ssot/` | 8 | 7 | ✅ Complete — doc generation inlined in routes |
| `api/assets/` | 6 | 5 | ✅ Complete — thumbnail inlined in upload |
| `api/kyc/` | 4 | 4 | ✅ Complete |
| `api/tests/` | 4 | 5 | ✅ Complete — split across functions |
| `app/src/app/` | ~20 | 10 | 🟡 Partial — public + admin dashboard + horses, auth |
| `app/src/lib/` | 3 | 4 | ✅ Complete — added utils.ts |
| `app/src/components/` | ~12 | 0 | 🔴 Not started |
| `dna/` | 8 | 8 | ✅ Complete — schemas + brand + conventions |
| Config | 5 | 6 | ✅ Complete — added BLOCKERS.md, GAME_PLAN.md, AGENTS.md |

---

## What's Built (with exact file paths)

### api/ — Cloud Functions (Python)

```
api/
├── requirements.txt                              ✅
├── models/__init__.py                             ✅ Horse, Owner, Trainer, HLT, Asset, LoveracingRef
├── ssot/
│   ├── main.py                                   ✅ Router: /horses, /owners, /trainers, /hlts, /docs
│   ├── routes/__init__.py                         ✅
│   ├── routes/horses.py                           ✅ CRUD by microchip, age computed, name_slug auto
│   ├── routes/owners.py                           ✅ CRUD, delete blocked if HLTs reference
│   ├── routes/trainers.py                         ✅ CRUD, delete blocked if horses reference
│   ├── routes/hlts.py                             ✅ CRUD + status transition validation
│   ├── routes/docs.py                             ✅ Generate Term Sheet, PDS, SA (DOCX)
│   └── tests/
│       ├── test_horses.py                         ✅ Model validation + route mock
│       ├── test_owners.py                         ✅ Model validation
│       └── test_hlt.py                            ✅ Model validation + status transitions
├── assets/
│   ├── main.py                                   ✅ Router: /upload, /retrieve, /delete
│   ├── routes/__init__.py                         ✅
│   ├── routes/upload.py                           ✅ Multipart upload, thumbnail, is_primary
│   ├── routes/retrieve.py                         ✅ Get by entity_type + entity_id
│   ├── routes/delete_asset.py                     ✅ Remove from GCS + Firestore
│   └── tests/test_assets.py                      ✅ Model validation
└── kyc/
    ├── main.py                                   ✅ Router: /create-session, /webhook
    ├── routes/__init__.py                         ✅
    ├── routes/create_session.py                   ✅ Stripe Identity session creation
    ├── routes/webhook.py                          ✅ Stripe webhook handler
    └── tests/test_kyc.py                          ✅ Session + webhook validation
```

### app/ — Next.js 16 + App Router

```
app/
├── package.json                                   ✅ next, react, firebase, stripe, lucide, tailwind
├── next.config.ts                                 ✅ API rewrites to Cloud Functions
├── tsconfig.json                                  ✅
├── tailwind.config.ts                             ✅ Gold + Evolution color palette
├── postcss.config.mjs                             ✅
└── src/
    ├── app/
    │   ├── globals.css                             ✅ Tailwind + brand colors + scrollbar
    │   ├── layout.tsx                              ✅ Root layout (dark theme, Playfair + Inter)
    │   ├── (public)/
    │   │   ├── page.tsx                            ✅ Home page (hero, features, CTA)
    │   │   ├── about/page.tsx                      ✅ About page (principles, data source)
    │   │   └── press/page.tsx                      ✅ Press page (placeholder)
    │   ├── admin/
    │   │   ├── layout.tsx                          ✅ Sidebar layout
    │   │   ├── page.tsx                            ✅ Dashboard (register horse, owners, HLTs)
    │   │   └── horses/
    │   │       ├── page.tsx                        ✅ Horse list with table
    │   │       └── new/page.tsx                    ✅ Horse intake form with loveracing.nz lookup
    │   └── auth/
    │       ├── layout.tsx                          ✅ Centered card layout
    │       ├── login/page.tsx                      ✅ Login form (Firebase Auth)
    │       └── verify/page.tsx                     ✅ KYC verification status (Stripe Identity)
    └── lib/
        ├── api.ts                                  ✅ Full API client (horses, owners, trainers, hlts, assets, kyc)
        ├── auth.ts                                 ✅ Firebase Auth + role/KYC status helpers
        ├── stripe.ts                               ✅ Stripe.js loader + redirect helper
        └── utils.ts                                ✅ cn(), formatMicrochip(), calculateAge(), loveracingUrl()
```

### dna/ — Design System + Schemas

```
dna/
├── brand/
│   ├── BRAND_SYSTEM.md                            ✅ Colors, typography, spacing, components
│   └── VOICE_SYSTEM.md                            ✅ Voice principles, terminology, tone by context
├── conventions/
│   └── CONVENTIONS.md                              ✅ Naming, API patterns, data conventions, security
└── schemas/
    ├── horse.json                                  ✅ JSON Schema for horse record
    ├── owner.json                                  ✅ JSON Schema for owner
    ├── trainer.json                                ✅ JSON Schema for trainer
    ├── hlt.json                                    ✅ JSON Schema for HLT (with status lifecycle)
    └── asset.json                                  ✅ JSON Schema for assets (extensible entity types)
```

### Workspace Config

```
evolution/
├── README.md                                      ✅ Quick start + architecture rules
├── AGENTS.md                                      ✅ Agent orchestration rules (6 core laws)
├── BLOCKERS.md                                    ✅ 4 human handoff points (GCP, Stripe, Firebase, deploy)
├── GAME_PLAN.md                                   ✅ 9 checkpoints with verification commands
└── Justfile                                       ✅ Build, test, deploy commands
```

---

## What's NOT Built Yet (20 files remaining)

### Missing Admin Pages (8 files)

| File | Purpose | Priority |
|------|---------|----------|
| `app/src/app/admin/owners/page.tsx` | Owner list + create | High |
| `app/src/app/admin/owners/new/page.tsx` | Owner intake form | High |
| `app/src/app/admin/trainers/page.tsx` | Trainer list + create | High |
| `app/src/app/admin/trainers/new/page.tsx` | Trainer intake form | High |
| `app/src/app/admin/hlts/page.tsx` | HLT list + create | High |
| `app/src/app/admin/hlts/new/page.tsx` | HLT assembly form | High |
| `app/src/app/admin/assets/page.tsx` | Asset upload + browse | Medium |
| `app/src/app/admin/horses/[microchip]/page.tsx` | Horse detail + images | Medium |

### Missing Components (12 files)

| File | Purpose | Priority |
|------|---------|----------|
| `app/src/components/ui/button.tsx` | Button component | High |
| `app/src/components/ui/card.tsx` | Card component | High |
| `app/src/components/ui/input.tsx` | Input component | High |
| `app/src/components/ui/table.tsx` | Table component | High |
| `app/src/components/ui/dialog.tsx` | Dialog component | Medium |
| `app/src/components/ui/badge.tsx` | Badge component | Medium |
| `app/src/components/layout/navbar.tsx` | Public navbar | High |
| `app/src/components/layout/sidebar.tsx` | Admin sidebar | Medium |
| `app/src/components/layout/footer.tsx` | Public footer | Medium |
| `app/src/components/horse/horse-card.tsx` | Horse card | Medium |
| `app/src/components/horse/horse-form.tsx` | Horse form fields | Medium |
| `app/src/components/horse/image-gallery.tsx` | Horse image gallery | Medium |

---

## Design Decisions That Changed from the Plan

| Decision | Plan Said | What We Built | Why |
|----------|-----------|---------------|-----|
| Models location | `models/horse.py`, `models/owner.py`, etc. | `models/__init__.py` (single file) | Fewer files, easier imports, all models are small |
| Auth roles | 2 roles (admin, viewer) | 3 roles (admin, investor, viewer) | Matches Step 2 needs, no cost to add now |
| API proxy | `app/src/api/` thin proxy routes | `next.config.ts` rewrites | No code duplication, simpler deployment |
| Doc generation | Separate `doc_generator.py` | Inlined in `routes/docs.py` | Fewer files, same logic |
| Thumbnail generation | Separate `image_utils.py` | Inlined in `routes/upload.py` | Fewer files, same logic |
| HLT horse field | `horseMicrochip` | `horse_id` | Consistent naming with other ID fields |

---

## loveracing.nz Data Mapping (Discovered During Build)

The Stud Book page at `https://loveracing.nz/Breeding/{HorseID}/{NameSlug}.aspx` provides:

| loveracing.nz Field | Our Field | Example (Prudentia NZ) |
|---------------------|-----------|----------------------|
| HorseID (URL param) | `loveracing_ref.loveracing_id` | 427416 |
| Name (page title) | `name` | Prudentia (NZ) |
| Born | `foaling_date` | 13/11/2021 |
| Age | Computed from `foaling_date` | 4YO |
| Sex + Colour | `sex`, `colour` | Bay Mare |
| Sire (link) | `sire_name`, `sire_id` | PROISIR (AUS) 2009 |
| Dam (link) | `dam_name`, `dam_id` | LITTLE BIT IRISH (NZ) 2012 |
| Family | `family_number` | 13 |
| DNA Typed | `dna_typed` | Y |
| PV | `pv` | Y |
| Microchip | `microchip` | 985125000126462 |
| Life no | `loveracing_ref.life_number` | NZ00427416 |
| Left shoulder | `left_shoulder_brand` | KB INSIDE CIRCLE |
| Right shoulder | `right_shoulder_brand` | 85 OVER 1 |
| Breeder | `breeder` | Goldeye Trust |

This mapping is captured in the `LoveracingRef` Pydantic model and the `horse.json` JSON Schema.

---

## Verification Commands

```bash
# Checkpoint 1: Firestore + Storage (requires gcloud auth)
gcloud firestore databases list
gsutil ls gs://evolution-horse-images
gsutil ls gs://evolution-horse-docs

# Checkpoint 2: Pydantic Models
cd api && pytest models/ -v

# Checkpoint 3: SSOT API (Horses)
curl -X POST http://localhost:8080/horses \
  -H "Content-Type: application/json" \
  -d '{"microchip": "985125000126462", "name": "Prudentia NZ", "foaling_date": "2021-11-13", "sex": "mare", "colour": "Bay"}'

# Checkpoint 4: SSOT API (Owners, Trainers, HLTs, Docs)
curl -X POST http://localhost:8080/owners -d '{"name": "Goldeye Trust", "email": "trust@example.com", "type": "syndicate"}'
curl -X POST http://localhost:8080/trainers -d '{"name": "Sam Bergerson", "stableName": "Evolution Stables"}'
curl -X POST http://localhost:8080/hlts -d '{"horse_id": "985125000126462", "owner_id": "...", "trainer_id": "..."}'

# Checkpoint 5: Assets API
curl -X POST http://localhost:8081/upload -F "file=@horse.jpg" -F "entity_type=horse" -F "entity_id=985125000126462"

# Checkpoint 6: KYC API
curl -X POST http://localhost:8082/create-session -d '{"user_id": "...", "return_url": "..."}'

# Checkpoint 7: Next.js App (Public)
cd app && npm run dev
# Visit http://localhost:3000

# Checkpoint 8: Next.js App (Admin + Auth)
# Visit http://localhost:3000/admin
# Visit http://localhost:3000/auth/login

# Checkpoint 9: Integration Test
cd api && pytest -v
cd app && npm test
```