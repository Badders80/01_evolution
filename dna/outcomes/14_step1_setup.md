# Step 1 MVP: The Minimal Setup

**Date:** 2026-05-19
**Principle:** Build the minimum that works. Design the data model for the future. Don't build code you don't need yet.

---

## The Mental Model

Think of it as three layers, not four:

```
┌─────────────────────────────────────────┐
│  app/          What the user sees        │  ← Build now: public + admin + auth
│  (Next.js)     and interacts with        │  ← Design for: marketplace, mystable
├─────────────────────────────────────────┤
│  api/          What touches data         │  ← Build now: horses, owners, assets, kyc
│  (Functions)   and enforces rules        │  ← Design for: token, content, ops
├─────────────────────────────────────────┤
│  infra/        What runs the cloud       │  ← Build now: Firestore, Storage, Auth
│  (Terraform)   and keeps secrets         │  ← Design for: pipelines, monitoring
└─────────────────────────────────────────┘
```

The **data model** is where you design for the future. The **code** is where you build only what you need.

---

## What You Actually Build Right Now

### 1. Firestore — 5 Collections, That's It

```javascript
// horses — the anchor. Everything hangs off microchip.
{
  id: string,                  // auto-generated
  microchip: string,           // UNIQUE. The durable anchor. Never changes.
  name: string,
  age: number,
  breed: string,
  sex: string,                 // "colt", "filly", "gelding", "mare", "stallion"
  trainerId: string,            // → trainers.id
  imageUrl: string | null,     // primary image GCS URL
  status: "active" | "retired" | "deceased",
  createdAt: timestamp,
  updatedAt: timestamp
}

// owners — independent. Linked by ID, not inlined.
{
  id: string,
  name: string,
  email: string,
  phone: string | null,
  type: "individual" | "syndicate" | "corporate",
  createdAt: timestamp,
  updatedAt: timestamp
}

// trainers — independent. Linked by ID, not inlined.
{
  id: string,
  name: string,
  stableName: string,
  location: string,
  email: string,
  phone: string | null,
  createdAt: timestamp,
  updatedAt: timestamp
}

// hlts — horse + lease terms assembled together
// DESIGNED FOR LATER: the "status" field is how we gate marketplace.
//   draft → reviewed → publish_ready → published
//   Step 1 only uses draft and reviewed. publish_ready and published come in Step 2.
{
  id: string,
  horseMicrochip: string,       // → horses.microchip
  ownerId: string,              // → owners.id
  trainerId: string,             // → trainers.id
  leasePeriodMonths: number,
  leaseStartDate: date,
  leaseholdStakePercentage: number,
  investorReturnPercentage: number,
  syndicatePriceCents: number,
  sharesTotal: number,
  sharesSold: number,            // Step 1: always 0. Step 2: updated by Token
  sharePriceCents: number,
  currency: "NZD",
  status: "draft" | "reviewed" | "publish_ready" | "published",
  documents: {
    termSheet: { status: "pending" | "reviewed", gcsUrl: string | null },
    pds: { status: "pending" | "reviewed", gcsUrl: string | null },
    sa: { status: "pending" | "reviewed", gcsUrl: string | null }
  },
  createdAt: timestamp,
  updatedAt: timestamp
}

// assets — images and docs attached to any entity
// DESIGNED FOR LATER: entityType can be "horse", "owner", "trainer", "hlt", "marketplace"
//   Step 1 only uses "horse". The rest come when needed.
{
  id: string,
  entityType: "horse" | "owner" | "trainer" | "hlt" | "marketplace",
  entityId: string,              // microchip for horse, id for others
  assetType: "image" | "document",
  gcsUrl: string,                // full GCS path
  thumbnailUrl: string | null,  // resized version (generated on upload)
  alt: string,
  tags: string[],                // ["headshot", "racing", "paddock"]
  isPrimary: boolean,
  uploadedBy: string,            // user ID
  createdAt: timestamp
}
```

**What's NOT in Step 1 but the schema supports:**
- `users` collection — comes when you add Firebase Auth for investors
- `investments` collection — comes with Token (Step 2)
- `leads` collection — comes with CRM (Step 4)
- `content` collection — comes with Content pipeline (Step 3)

The `status` field on `hlts` is the key design-for-later decision. It has four states, but Step 1 only uses `draft` and `reviewed`. When marketplace comes in Step 2, `publish_ready` and `published` naturally extend it — no schema change needed.

---

### 2. Cloud Storage — 2 Buckets

```
evolution-horse-images/     ← Horse images, organized by microchip
  └── {microchip}/
      ├── primary.jpg
      ├── racing-001.jpg
      └── paddock-002.jpg

evolution-horse-docs/        ← Generated DOCX files
  └── {hlt-id}/
      ├── term-sheet.docx
      ├── pds.docx
      └── sa.docx
```

That's it. Two buckets. No content pipeline buckets yet. No video buckets yet. Those come in Step 3.

---

### 3. Cloud Functions — 3 Functions, Not 6

Don't split into micro-functions yet. Start with 3 logical groupings:

```
api/
├── ssot/                    ← ONE function: horses, owners, trainers, hlts, docs
│   ├── main.py              ← Cloud Function entry point
│   ├── models.py            ← Pydantic schemas (shared)
│   ├── routes/
│   │   ├── horses.py        ← CRUD
│   │   ├── owners.py        ← CRUD
│   │   ├── trainers.py      ← CRUD
│   │   ├── hlts.py          ← CRUD + status transitions
│   │   └── docs.py          ← Generate Term Sheet, PDS, SA
│   ├── doc_generator.py     ← docx library logic
│   ├── requirements.txt     ← google-cloud-firestore, docx, pydantic
│   └── tests/
│       ├── test_horses.py
│       ├── test_owners.py
│       ├── test_hlt.py
│       └── test_docs.py
│
├── assets/                  ← ONE function: upload, retrieve, delete
│   ├── main.py
│   ├── models.py             ← Asset Pydantic schema
│   ├── routes/
│   │   ├── upload.py         ← Upload to GCS + write Firestore metadata
│   │   ├── retrieve.py       ← Get by entity (microchip for horses)
│   │   └── delete.py         ← Remove from GCS + Firestore
│   ├── image_utils.py        ← Thumbnail generation on upload
│   ├── requirements.txt     ← google-cloud-storage, google-cloud-firestore, pillow
│   └── tests/
│       └── test_assets.py
│
└── kyc/                     ← ONE function: Stripe Identity
    ├── main.py
    ├── routes/
    │   ├── create_session.py ← Create Stripe Identity verification session
    │   └── webhook.py        ← Handle Stripe webhook for KYC result
    ├── requirements.txt     ← stripe, google-cloud-firestore
    └── tests/
        └── test_kyc.py
```

**Why 3, not 6?** Each function is a deployable unit. Right now, the traffic is low. When you need to scale `assets` independently, split it. But don't split before you have traffic.

**What's NOT in Step 1:**
- `state/` function — comes with agent orchestration (Step 3)
- `content/` function — comes with content pipeline (Step 3)
- `token/` function — comes with marketplace (Step 2)
- `studio/` function — comes with production engine (Step 3)

---

### 4. Next.js App — 3 Route Groups

```
app/
├── src/
│   ├── app/
│   │   ├── (public)/           ← GROUP 1: No auth required
│   │   │   ├── layout.tsx      ← Public layout: nav, footer
│   │   │   ├── page.tsx        ← Home
│   │   │   ├── about/
│   │   │   │   └── page.tsx
│   │   │   └── press/
│   │   │       └── page.tsx
│   │   │
│   │   ├── admin/              ← GROUP 2: Admin auth required
│   │   │   ├── layout.tsx      ← Admin layout: sidebar, auth guard
│   │   │   ├── page.tsx        ← Dashboard
│   │   │   ├── horses/
│   │   │   │   ├── page.tsx    ← List + create
│   │   │   │   └── [microchip]/
│   │   │   │       ├── page.tsx    ← Detail + images
│   │   │   │       └── edit/
│   │   │   │           └── page.tsx
│   │   │   ├── owners/
│   │   │   │   ├── page.tsx
│   │   │   │   └── [id]/
│   │   │   │       └── page.tsx
│   │   │   ├── trainers/
│   │   │   │   ├── page.tsx
│   │   │   │   └── [id]/
│   │   │   │       └── page.tsx
│   │   │   ├── hlts/
│   │   │   │   ├── page.tsx    ← List + create
│   │   │   │   └── [id]/
│   │   │   │       ├── page.tsx    ← Detail + doc generation
│   │   │   │       └── review/
│   │   │   │           └── page.tsx  ← Accept/Amend per section
│   │   │   └── assets/
│   │   │       └── page.tsx    ← Upload, browse, tag images
│   │   │
│   │   ├── auth/               ← GROUP 3: Auth flows
│   │   │   ├── login/
│   │   │   │   └── page.tsx
│   │   │   └── verify/
│   │   │       └── page.tsx    ← Stripe KYC flow
│   │   │
│   │   └── api/                ← Thin proxies to Cloud Functions
│   │       ├── horses/
│   │       ├── owners/
│   │       ├── trainers/
│   │       ├── hlts/
│   │       ├── assets/
│   │       └── kyc/
│   │
│   ├── lib/
│   │   ├── auth.ts            ← Firebase Auth config + role checks
│   │   ├── api.ts             ← Typed fetch wrapper for Cloud Functions
│   │   └── stripe.ts          ← Stripe publishable key + helpers
│   │
│   └── components/
│       ├── ui/                ← shadcn/ui (button, card, input, table, dialog)
│       ├── horse/             ← HorseCard, HorseForm, HorseImageGallery
│       ├── hlt/               ← HLTWizard, DocReviewSection
│       ├── asset/             ← ImageUpload, ImageGrid, ImageTagger
│       └── layout/            ← Navbar, Sidebar, Footer
│
├── public/                    ← Brand images, favicon, OG images
├── tests/
├── next.config.ts
├── tailwind.config.ts
├── vitest.config.ts
└── package.json
```

**What's NOT in Step 1 but the route structure supports:**
- `/marketplace/` — comes in Step 2, just add the route group
- `/mystable/` — comes in Step 2, just add the route group
- `/admin/marketplace/` — comes in Step 2, just add the route group
- `/admin/content/` — comes in Step 3, just add the route group

The `(public)`, `admin`, and `auth` route groups are the permanent structure. Everything else is additive.

---

### 5. Auth — Firebase Auth, 2 Roles

```typescript
// Step 1: Two roles only
type UserRole = "admin" | "viewer";

// Step 2: Add investor role
// type UserRole = "admin" | "investor" | "viewer";

// Step 3+: Add syndicator role
// type UserRole = "admin" | "syndicator" | "investor" | "viewer";
```

Step 1 auth flow:
1. Admin signs in with email/password via Firebase Auth
2. Custom claim `role: "admin"` set on the user
3. Admin can access `/admin/*` routes
4. Everyone can access `(public)/*` routes
5. KYC verification is a separate Stripe flow (not Firebase Auth)

**What's NOT in Step 1:**
- Investor self-registration (comes with marketplace)
- Wallet-based auth (comes with Token Stage 2)
- Social login (comes when needed)

---

### 6. DNA — Schemas Only

```
dna/
├── brand/
│   ├── BRAND_SYSTEM.md        ← Colors, typography, voice
│   └── VOICE_SYSTEM.md        ← Tone, language
├── schemas/
│   ├── horse.json             ← JSON Schema for horse record
│   ├── owner.json             ← JSON Schema for owner record
│   ├── trainer.json           ← JSON Schema for trainer record
│   ├── hlt.json               ← JSON Schema for HLT record
│   └── asset.json             ← JSON Schema for asset metadata
└── conventions/
    └── CONVENTIONS.md         ← Naming, file structure, coding style
```

The schemas are the contract between `api/models/` (Pydantic) and `app/src/components/` (React forms). Both validate against the same schema. No drift possible.

---

## What You DON'T Build in Step 1

| Thing | Why Not | When |
|-------|---------|------|
| Terraform | Manual `gcloud` is fine for 3 functions | Step 2 (when you have 6+ functions) |
| CI/CD pipeline | Manual deploy is fine for MVP | Step 2 (when you have automated tests) |
| Agent orchestration | No agents yet | Step 3 |
| Content pipeline | No content scraping yet | Step 3 |
| Marketplace UI | No published HLTs yet | Step 2 |
| MyStable dashboard | No investors yet | Step 2 |
| Stripe payments | KYC first, payments later | Step 2 |
| Smart contracts | Stage 2 feature | Step 5 |
| CRM | Spreadsheet is fine for now | Step 4 |
| GST/ops pipeline | Manual is fine for now | Step 4 |
| Monitoring dashboard | Cloud Console is fine for now | Step 2 |
| Vertex AI Search | No content to search yet | Step 3 |

---

## The Build Order (Testable Checkpoints)

Each checkpoint produces something you can verify.

### Checkpoint 1: Firestore + Storage
```bash
# What you do
gcloud app create --region=australia-southeast1
gcloud firestore databases create --region=australia-southeast1
gsutil mb gs://evolution-horse-images
gsutil mb gs://evolution-horse-docs

# How you verify
gcloud firestore databases list
gsutil ls gs://evolution-horse-images
gsutil ls gs://evolution-horse-docs
```

### Checkpoint 2: Pydantic Models
```bash
# What you do
cd api/models/
# Write horse.py, owner.py, trainer.py, hlt.py, asset.py

# How you verify
pytest api/models/tests/ -v
# All models validate, serialize, and deserialize correctly
```

### Checkpoint 3: SSOT API (Horses)
```bash
# What you do
cd api/ssot/
# Write main.py, routes/horses.py
gcloud functions deploy ssot --runtime python312 --trigger-http

# How you verify
curl -X POST https://REGION-PROJECT.cloudfunctions.net/ssot/horses \
  -H "Content-Type: application/json" \
  -d '{"microchip": "123456789012345", "name": "First Gear", "age": 4, "breed": "Thoroughbred", "sex": "gelding"}'
# Returns 201 with created horse
```

### Checkpoint 4: SSOT API (Owners, Trainers, HLTs, Docs)
```bash
# What you do
# Add routes/owners.py, routes/trainers.py, routes/hlts.py, routes/docs.py
# Redeploy ssot function

# How you verify
curl -X POST .../ssot/owners -d '{"name": "Alex", "email": "alex@evolution.nz"}'
curl -X POST .../ssot/trainers -d '{"name": "Sam", "stableName": "Evolution Stables"}'
curl -X POST .../ssot/hlts -d '{"horseMicrochip": "123456789012345", "ownerId": "...", ...}'
curl -X POST .../ssot/docs/term-sheet -d '{"hltId": "..."}'
# Returns DOCX file URL in GCS
```

### Checkpoint 5: Assets API
```bash
# What you do
cd api/assets/
# Write main.py, routes/upload.py, routes/retrieve.py, routes/delete.py
gcloud functions deploy assets --runtime python312 --trigger-http

# How you verify
curl -X POST .../assets/upload -F "file=@horse.jpg" -F "entityType=horse" -F "entityId=123456789012345"
# Returns asset metadata with GCS URL
curl .../assets/retrieve?entityType=horse&entityId=123456789012345
# Returns list of images for that horse
```

### Checkpoint 6: KYC API
```bash
# What you do
cd api/kyc/
# Write main.py, routes/create_session.py, routes/webhook.py
gcloud functions deploy kyc --runtime python312 --trigger-http

# How you verify
curl -X POST .../kyc/create-session -d '{"userId": "...", "returnUrl": "..."}'
# Returns Stripe Identity verification URL
```

### Checkpoint 7: Next.js App (Public Pages)
```bash
# What you do
cd app/
npx create-next-app@latest . --typescript --tailwind --app --src-dir
# Add (public)/ routes: home, about, press
# Add dna/brand/ styling

# How you verify
npm run dev
# Visit http://localhost:3000 — see clean marketing pages
```

### Checkpoint 8: Next.js App (Admin + Auth)
```bash
# What you do
# Add admin/ routes: horses, owners, trainers, hlts, assets
# Add auth/ routes: login, verify
# Add Firebase Auth config
# Add API proxy routes

# How you verify
# Visit /admin/horses — create a horse
# Visit /admin/horses/[microchip] — see horse detail + upload image
# Visit /admin/hlts — create HLT, generate docs
# Visit /auth/login — sign in as admin
# Visit /auth/verify — start Stripe KYC flow
```

### Checkpoint 9: Integration Test
```bash
# What you do
# Write end-to-end test: create horse → create owner → create HLT → generate docs → upload image

# How you verify
pytest api/ssot/tests/ -v
pytest api/assets/tests/ -v
pytest api/kyc/tests/ -v
cd app/ && npm test
# All tests pass
```

---

## The "One Eye on the Future" Checklist

These are decisions made NOW that affect LATER. Get them right and everything else is additive.

| Decision | Made Now | Affects Later |
|----------|----------|---------------|
| Microchip as horse primary key | ✅ | Marketplace, Token, Content all reference by microchip |
| HLT status: `draft → reviewed → publish_ready → published` | ✅ | Marketplace reads `published` HLTs. No schema change needed. |
| `entityType` on assets: `"horse" \| "owner" \| ...` | ✅ | Marketplace images, content images — just add a new entityType |
| Firestore (not SQLite) | ✅ | Multi-user, real-time, cloud-accessible from day one |
| Cloud Functions (not Express server) | ✅ | Scale independently, pay per invocation |
| One Next.js app with route groups | ✅ | Marketplace and MyStable are just new route groups |
| Firebase Auth with custom claims | ✅ | Add `investor` and `syndicator` roles later |
| `api/` as the only data writer | ✅ | No direct Firestore access from the app. Ever. |
| JSON Schemas in `dna/schemas/` | ✅ | Pydantic and React forms both validate against the same schema |
| GCS for images (not local filesystem) | ✅ | CDN-ready, searchable by metadata in Firestore |

---

## File Count for Step 1

This is the total number of files you need to write:

| Layer | Files | Purpose |
|-------|-------|---------|
| `api/models/` | 6 | Pydantic schemas + `__init__.py` |
| `api/ssot/` | 8 | main.py, 5 routes, requirements.txt, doc_generator.py |
| `api/assets/` | 6 | main.py, 3 routes, image_utils.py, requirements.txt |
| `api/kyc/` | 4 | main.py, 2 routes, requirements.txt |
| `api/tests/` | 4 | One test file per function |
| `app/src/app/` | ~20 | Routes, layouts, pages |
| `app/src/lib/` | 3 | auth.ts, api.ts, stripe.ts |
| `app/src/components/` | ~12 | UI components |
| `dna/` | 8 | 5 schemas, 2 brand docs, 1 conventions doc |
| Config | 5 | package.json, next.config.ts, tailwind.config.ts, vitest.config.ts, Justfile |
| **Total** | **~76** | |

76 files. That's the minimum viable business surface. Not 12 projects. Not 200 files. 76.

---

## What Comes After Step 1

| Step | What You Add | Files Added |
|------|-------------|-------------|
| Step 2 | Marketplace + Stripe payments + investor auth | ~30 files (new routes, new API function, smart contracts) |
| Step 3 | Content pipeline + Studio production + agent orchestration | ~40 files (new functions, pipelines, state API) |
| Step 4 | Ops (GST, banking) + CRM | ~20 files (new functions, new routes) |
| Step 5 | Token Stage 2 (on-chain) | ~15 files (smart contracts, wallet integration) |

Each step is additive. No step requires rewriting what came before.