# Step 1: Minimum Viable Business Surface

**Date:** 2026-05-19
**Scope:** Clean website, Stripe KYC, horse/owner intake, image asset centre
**Not in scope:** Marketplace, tokenization, content pipeline, full agent layer, Ops, CRM

---

## What You're Actually Building

Four things, and only four things:

1. **A clean public website** — Marketing pages that look professional
2. **Stripe KYC** — Identity verification so investors can be verified
3. **Horse/owner intake** — A way to author horse records, owners, trainers, and generate the three legal docs (Term Sheet, PDS, Syndicate Agreement)
4. **An asset centre** — Upload images to a horse, retrieve them easily, use them on the website

That's it. No marketplace. No tokenization. No content scraping pipeline. No agent orchestration. Those come later.

---

## The Structure for Step 1

```
evolution/                          ← Single workspace
├── infra/                          ← Terraform: creates the cloud footprint
│   ├── main.tf                     ← GCP project, Firestore, Storage buckets
│   ├── firestore.tf                ← Collections, indexes, security rules
│   ├── storage.tf                 ← Buckets: horse-images, horse-docs
│   └── secrets.tf                  ← Stripe keys, Firebase config
│
├── api/                            ← Cloud Functions: the only data writers
│   ├── models/                    ← SHARED: all Pydantic schemas live here
│   │   ├── horse.py               ← Horse identity (microchip anchor)
│   │   ├── owner.py               ← Owner record
│   │   ├── trainer.py             ← Trainer/stable record
│   │   ├── hlt.py                 ← HLT = horse + lease terms
│   │   ├── user.py                ← User + KYC status
│   │   ├── asset.py               ← Image/document metadata
│   │   └── __init__.py            ← Single import point
│   │
│   ├── ssot/                      ← Horse, Owner, Trainer, HLT CRUD
│   │   ├── main.py                ← Cloud Function (HTTP)
│   │   ├── routes/
│   │   │   ├── horses.py          ← CRUD: create, read, update, list
│   │   │   ├── owners.py          ← CRUD: create, read, update, list
│   │   │   ├── trainers.py        ← CRUD: create, read, update, list
│   │   │   ├── hlts.py            ← CRUD: create, read, update, list, publish
│   │   │   └── docs.py            ← Generate Term Sheet, PDS, SA
│   │   └── tests/
│   │       ├── test_horses.py
│   │       ├── test_owners.py
│   │       ├── test_hlt.py
│   │       └── test_docs.py
│   │
│   ├── assets/                    ← Image upload + retrieval
│   │   ├── main.py                ← Cloud Function (HTTP)
│   │   ├── routes/
│   │   │   ├── upload.py           ← Upload image to GCS, write metadata to Firestore
│   │   │   ├── retrieve.py         ← Get images for a horse by microchip
│   │   │   └── delete.py           ← Remove image + metadata
│   │   └── tests/
│   │       └── test_assets.py
│   │
│   ├── kyc/                       ← Stripe Identity verification
│   │   ├── main.py                ← Cloud Function (HTTP)
│   │   ├── routes/
│   │   │   ├── create_session.py  ← Create Stripe Identity verification session
│   │   │   └── webhook.py          ← Handle Stripe KYC webhook
│   │   └── tests/
│   │       └── test_kyc.py
│   │
│   └── state/                     ← Agent state (minimal, for future use)
│       ├── main.py                ← Cloud Function (HTTP: CRUD)
│       └── tests/
│           └── test_state.py
│
├── app/                           ← Single Next.js application
│   ├── src/
│   │   ├── app/
│   │   │   ├── (public)/          ← Marketing pages: home, about, press
│   │   │   │   ├── page.tsx       ← Home
│   │   │   │   ├── about/
│   │   │   │   │   └── page.tsx   ← About
│   │   │   │   └── press/
│   │   │   │       └── page.tsx   ← Press
│   │   │   │
│   │   │   ├── admin/             ← Horse/owner intake + asset management
│   │   │   │   ├── layout.tsx     ← Auth guard (Firebase Auth + admin role)
│   │   │   │   ├── page.tsx       ← Dashboard
│   │   │   │   ├── horses/
│   │   │   │   │   ├── page.tsx   ← Horse list
│   │   │   │   │   └── [id]/
│   │   │   │   │       ├── page.tsx   ← Horse detail + images
│   │   │   │   │       └── edit/
│   │   │   │   │           └── page.tsx   ← Edit horse
│   │   │   │   ├── owners/
│   │   │   │   │   ├── page.tsx   ← Owner list
│   │   │   │   │   └── [id]/
│   │   │   │   │       └── page.tsx   ← Owner detail
│   │   │   │   ├── trainers/
│   │   │   │   │   ├── page.tsx   ← Trainer list
│   │   │   │   │   └── [id]/
│   │   │   │   │       └── page.tsx   ← Trainer detail
│   │   │   │   ├── hlts/
│   │   │   │   │   ├── page.tsx   ← HLT list
│   │   │   │   │   └── [id]/
│   │   │   │   │       ├── page.tsx   ← HLT detail + doc generation
│   │   │   │   │       └── review/
│   │   │   │   │           └── page.tsx   ← Human-in-the-loop review
│   │   │   │   └── assets/
│   │   │   │       └── page.tsx   ← Asset centre: upload, browse, tag
│   │   │   │
│   │   │   ├── auth/
│   │   │   │   ├── login/page.tsx  ← Login
│   │   │   │   └── verify/page.tsx ← KYC verification flow
│   │   │   │
│   │   │   └── api/               ← Next.js API routes (thin proxies to api/)
│   │   │       ├── horses/
│   │   │       ├── owners/
│   │   │       ├── trainers/
│   │   │       ├── hlts/
│   │   │       ├── assets/
│   │   │       └── kyc/
│   │   │
│   │   ├── lib/
│   │   │   ├── auth.ts            ← Firebase Auth + custom claims
│   │   │   ├── api.ts             ← Typed client for all api/ functions
│   │   │   ├── stripe.ts          ← Stripe client-side helpers
│   │   │   └── db.ts              ← Firestore client (read-only for app)
│   │   │
│   │   └── components/
│   │       ├── ui/                ← shadcn/ui components
│   │       ├── horse/             ← Horse card, horse form, image gallery
│   │       ├── owner/             ← Owner form
│   │       ├── hlt/               ← HLT wizard, doc review
│   │       └── layout/            ← Nav, sidebar, footer
│   │
│   ├── public/                    ← Static assets (brand images, favicon)
│   ├── tests/
│   │   ├── horses.test.tsx
│   │   ├── kyc.test.tsx
│   │   └── assets.test.tsx
│   ├── next.config.ts
│   ├── tailwind.config.ts
│   ├── vitest.config.ts
│   └── package.json
│
├── dna/                           ← Shared design system
│   ├── brand/
│   │   ├── BRAND_SYSTEM.md        ← Colors, typography, voice
│   │   └── VOICE_SYSTEM.md        ← Tone, language, messaging
│   ├── schemas/
│   │   ├── horse.json             ← JSON Schema for horse record
│   │   ├── owner.json             ← JSON Schema for owner record
│   │   ├── hlt.json               ← JSON Schema for HLT record
│   │   └── marketplace-payload.json ← JSON Schema for future Platform handoff
│   └── conventions/
│       └── CONVENTIONS.md         ← Naming, file structure, coding style
│
├── docs/                          ← All migration + strategy docs
│   ├── MIGRATION_GUIDE.md
│   ├── DESIRED_OUTCOMES.md
│   └── Migrate_Manager/           ← Extraction reports
│
├── Justfile                       ← Workspace-level commands
├── package.json                   ← Workspace-level deps
├── AGENTS.md                      ← Agent orchestration rules
├── BLOCKERS.md                    ← Human handoff points
└── GAME_PLAN.md                   ← Single source of truth for the build
```

---

## What Each Layer Does in Step 1

### `infra/` — One `terraform apply` Creates Everything

| Resource | Purpose |
|----------|---------|
| Firestore database | `horses`, `owners`, `trainers`, `hlts`, `users`, `assets`, `agent_state` |
| Firestore indexes | Query patterns for horse-by-microchip, owner-by-email, HLT-by-status |
| Firestore security rules | Admin-only write, authenticated read for KYC users |
| Cloud Storage bucket `evolution-horse-images` | Horse images, organized by microchip |
| Cloud Storage bucket `evolution-horse-docs` | Generated DOCX files |
| Secret Manager entries | `stripe-secret-key`, `stripe-webhook-secret`, `firebase-config` |
| Cloud Function deployments | All functions in `api/` |

### `api/` — The Only Data Writer

| Function | Routes | What It Does |
|----------|--------|-------------|
| `ssot` | `/horses`, `/owners`, `/trainers`, `/hlts`, `/docs` | CRUD for all domain entities + doc generation |
| `assets` | `/upload`, `/retrieve`, `/delete` | Upload images to GCS, write metadata to Firestore, retrieve by microchip |
| `kyc` | `/create-session`, `/webhook` | Create Stripe Identity session, handle KYC webhook |
| `state` | `/status`, `/dispatch` | Minimal agent state (future use) |

**Key constraint:** The Next.js app never writes to Firestore directly. It calls these API functions. This enforces unidirectional data flow from day one.

### `app/` — One Next.js Application

| Route | Who Sees It | What It Does |
|-------|-------------|-------------|
| `/` `/about` `/press` | Everyone | Clean marketing pages |
| `/admin/horses` | Admin only | Horse intake: create, edit, list |
| `/admin/horses/[id]` | Admin only | Horse detail + image gallery |
| `/admin/owners` | Admin only | Owner intake: create, edit, list |
| `/admin/trainers` | Admin only | Trainer intake: create, edit, list |
| `/admin/hlts` | Admin only | HLT assembly + doc generation |
| `/admin/hlts/[id]/review` | Admin only | Human-in-the-loop doc review |
| `/admin/assets` | Admin only | Upload, browse, tag images |
| `/auth/login` | Everyone | Firebase Auth login |
| `/auth/verify` | Authenticated users | Stripe KYC verification |

### `dna/` — Shared Truth

The `schemas/` directory is critical for Step 1. It defines the exact shape of every data entity as JSON Schemas. Both the Pydantic models (`api/models/`) and the Next.js forms (`app/src/components/`) reference these schemas. No schema drift possible.

---

## What Step 1 Delivers

| Capability | Delivered By | User Story |
|------------|-------------|------------|
| Clean public website | `app/` (public routes) | "A visitor sees a professional site" |
| Horse intake | `api/ssot` + `app/` (admin/horses) | "An admin creates a horse record anchored by microchip" |
| Owner/trainer intake | `api/ssot` + `app/` (admin/owners, trainers) | "An admin creates owner and trainer records" |
| HLT assembly | `api/ssot` + `app/` (admin/hlts) | "An admin assembles a horse + lease terms into an HLT" |
| Document generation | `api/ssot` (docs routes) | "An admin generates Term Sheet, PDS, SA from an HLT" |
| Human-in-the-loop review | `app/` (admin/hlts/[id]/review) | "An admin reviews and approves each doc section" |
| Image upload + retrieval | `api/assets` + `app/` (admin/assets) | "An admin uploads images to a horse and retrieves them" |
| KYC verification | `api/kyc` + `app/` (auth/verify) | "An investor verifies their identity via Stripe" |
| Auth | Firebase Auth + custom claims | "Admins see admin routes; investors see verify route" |

---

## What Step 1 Does NOT Deliver

| Capability | When | Why |
|------------|------|-----|
| Marketplace listings | Step 2 | Needs HLT data flowing first |
| Investor portfolio (MyStable) | Step 2 | Needs Stripe payments + holdings |
| Content scraping pipeline | Step 3 | Not needed for business operations |
| Video/image production | Step 3 | Studio is a workbench, not a launch requirement |
| GST/banking processing | Step 4 | Ops can wait |
| CRM | Step 4 | Can be a spreadsheet for now |
| Agent orchestration | Step 3+ | State API exists but is minimal |
| Smart contracts | Step 5 | Stage 2, after digital shares work |

---

## Firestore Collections for Step 1

```javascript
// horses — anchored by microchip number
{
  microchip: string,        // PRIMARY KEY — durable, never changes
  name: string,
  age: number,
  breed: string,
  trainerId: string,        // reference to trainers collection
  imageUrl: string,          // primary image URL in GCS
  status: "active" | "retired" | "deceased",
  createdAt: timestamp,
  updatedAt: timestamp
}

// owners — independent entities, linked by ID
{
  id: string,
  name: string,
  email: string,
  phone: string,
  type: "individual" | "syndicate" | "corporate",
  createdAt: timestamp,
  updatedAt: timestamp
}

// trainers — independent entities, linked by ID
{
  id: string,
  name: string,
  stableName: string,
  location: string,
  email: string,
  phone: string,
  createdAt: timestamp,
  updatedAt: timestamp
}

// hlts — horse + lease terms assembled together
{
  id: string,
  horseMicrochip: string,     // reference to horses collection
  ownerId: string,             // reference to owners collection
  trainerId: string,           // reference to trainers collection
  leasePeriodMonths: number,
  leaseStartDate: date,
  leaseholdStakePercentage: number,
  investorReturnPercentage: number,
  syndicatePriceCents: number,
  sharesTotal: number,
  sharesSold: number,
  sharePriceCents: number,
  currency: "NZD",
  status: "draft" | "reviewed" | "publish_ready" | "published",
  documents: {
    termSheet: { status: "pending" | "reviewed", url: string },
    pds: { status: "pending" | "reviewed", url: string },
    sa: { status: "pending" | "reviewed", url: string }
  },
  createdAt: timestamp,
  updatedAt: timestamp
}

// users — for auth and KYC
{
  id: string,
  email: string,
  displayName: string,
  role: "admin" | "investor" | "viewer",
  kycStatus: "not_started" | "pending" | "verified" | "failed",
  stripeIdentitySessionId: string | null,
  createdAt: timestamp,
  updatedAt: timestamp
}

// assets — images and documents attached to entities
{
  id: string,
  entityType: "horse" | "owner" | "trainer" | "hlt",
  entityId: string,            // reference to the entity (e.g., microchip for horse)
  assetType: "image" | "document",
  url: string,                 // GCS URL
  thumbnailUrl: string,       // GCS URL (resized)
  alt: string,                 // description
  tags: string[],              // e.g., ["headshot", "racing", "paddock"]
  isPrimary: boolean,
  uploadedBy: string,          // user ID
  createdAt: timestamp
}

// agent_state — minimal, for future use
{
  agentId: string,
  status: "idle" | "working" | "error",
  currentTask: string | null,
  lastHeartbeat: timestamp,
  lastEvent: map | null
}
```

---

## Build Order

The order matters. Each step produces something testable.

| Step | What | Testable Outcome |
|------|------|-----------------|
| 1 | `infra/main.tf` + `firestore.tf` + `storage.tf` | `terraform apply` creates Firestore + GCS buckets |
| 2 | `api/models/` (Pydantic schemas) | `pytest` passes for all models |
| 3 | `api/ssot/` (horses CRUD) | `curl POST /horses` creates a horse in Firestore |
| 4 | `api/ssot/` (owners, trainers CRUD) | `curl POST /owners` creates an owner |
| 5 | `api/ssot/` (HLTs + doc generation) | `curl POST /hlts` creates an HLT; `curl POST /docs/term-sheet` generates DOCX |
| 6 | `api/assets/` (upload + retrieve) | `curl POST /assets/upload` uploads an image to GCS |
| 7 | `api/kyc/` (Stripe Identity) | `curl POST /kyc/create-session` returns a Stripe verification URL |
| 8 | `app/` (public routes) | Visit `/`, `/about`, `/press` — see clean marketing pages |
| 9 | `app/` (admin routes) | Visit `/admin/horses` — create a horse, upload an image |
| 10 | `app/` (auth + KYC) | Visit `/auth/login` → `/auth/verify` — complete Stripe KYC |
| 11 | `dna/schemas/` | JSON Schemas validate all API inputs and form fields |

Each step is independently deployable and testable. No step depends on a later step.

---

## Key Decisions for Step 1

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Database | Firestore | Already scaffolded in vertex_workspace, real-time, agent-friendly |
| Auth | Firebase Auth + custom claims | Simple, works with Next.js, supports admin/investor roles |
| KYC | Stripe Identity | Already in Evolution_Token, proven, NZD-compatible |
| Image storage | Cloud Storage + Firestore metadata | Images in GCS, metadata in Firestore, retrieved by microchip |
| Doc generation | `docx` library (Node.js) | Already in SSOT_Build, proven, produces real DOCX |
| Frontend | Next.js 16 + App Router + shadcn/ui | Already in Platform/Token, team familiarity |
| API layer | Cloud Functions (Python) | Consistent with vertex_workspace, Pydantic validation |
| Testing | Vitest (frontend) + pytest (backend) | Industry standard, fast |
| CI/CD | Cloud Build | GCP-native, works with Terraform |

---

## Debt We're NOT Carrying Forward

| Old Pattern | New Pattern | Why |
|-------------|-------------|-----|
| JSON files + localStorage | Firestore | Multi-user, real-time, cloud-accessible |
| SQLite | Firestore | No local DB, no file locking, no sync issues |
| Two separate Next.js repos | One Next.js app with RBAC | No merge hell, no duplicate deps |
| Manual `git push` for deployment | Cloud Build + Pub/Sub | Auditable, rollback-able |
| Symlinked `.env` | Secret Manager | No secrets in git |
| No tests | pytest + Vitest from day one | Every API route has a test |
| No security rules | Firestore rules deployed with Terraform | Admin-only write, authenticated read |
| Bi-directional sync | Unidirectional API | SSOT API is the only writer |
| Multiple AI providers | Vertex AI (Gemini) for cloud, Ollama for local | Consolidated auth, consistent behavior |