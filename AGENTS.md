# Evolution — Agent Orchestration Rules

## Identity
You are the **Evolution Build Agent**. You build the minimum viable business surface for Evolution Stables.

## Core Laws
1. **`api/` is the only data writer.** The app never writes to Firestore directly.
2. **Microchip is the durable anchor.** Every horse is identified by its 15-digit microchip.
3. **HLT status is a state machine.** `draft → reviewed → publish_ready → published`. Step 1 only uses `draft` and `reviewed`.
4. **Assets are organized by entity.** `horse/{microchip}/` in GCS.
5. **DNA schemas are the contract.** Pydantic models and React forms both validate against the same JSON Schemas.
6. **No bi-directional sync.** Downstream systems are clients of the SSOT API. They POST updates; they don't sync back.

**Every law exists because the old workspace broke without it.** Read `dna/outcomes/WHY.md` before adding, removing, or "simplifying" any rule. Each law is grounded in a specific failure from the extraction reports in `dna/outcomes/`.

## Data Source
Every NZ thoroughbred has a loveracing.nz Stud Book page:
- URL: `https://loveracing.nz/Breeding/{HorseID}/{NameSlug}.aspx`
- Key fields: Microchip, Life Number, Name, Foaling Date, Sex, Colour, Sire, Dam, Breeder, Brands

## Build Order
1. Firestore + Storage (manual gcloud commands)
2. Pydantic models (api/models/)
3. SSOT API (horses → owners → trainers → HLTs → docs)
4. Assets API (upload → retrieve → delete)
5. KYC API (Stripe Identity)
6. Next.js app (public pages → admin → auth)

## Verification
Every task must end with a verification command and its output. No exceptions.

---

## 🛠️ Build & Test Commands

### API (Python Cloud Functions)

```bash
# Install dependencies
cd api && pip install -r requirements.txt

# Run locally
just run-ssot    # SSOT API on port 8080
just run-assets  # Assets API on port 8081
just run-kyc     # KYC API on port 8082

# Test
just test-api    # All API tests
just test-ssot   # SSOT tests only
just test-assets # Assets tests only
just test-kyc    # KYC tests only
```

### App (Next.js)

```bash
# Install dependencies
just install-app

# Run dev server
just dev-app

# Build for production
just build-app
```

### Deployment

```bash
# Deploy Cloud Functions (from api/ directory)
gcloud functions deploy ssot --runtime python311 --trigger-http --allow-unauthenticated --entry-point ssot --region australia-southeast1
gcloud functions deploy assets --runtime python311 --trigger-http --allow-unauthenticated --entry-point assets --region australia-southeast1
gcloud functions deploy kyc --runtime python311 --trigger-http --allow-unauthenticated --entry-point kyc --region australia-southeast1
```

---

## 🏗️ Architecture Overview

### Project Structure
```
evolution/
├── api/          Cloud Functions (the ONLY data writers)
│   ├── models/   Shared Pydantic schemas
│   ├── ssot/     Horse, Owner, Trainer, HLT, Doc generation
│   ├── assets/   Image upload, retrieve, delete (GCS)
│   └── kyc/      Stripe Identity verification
├── app/          Next.js 16 application (public + admin + auth)
│   └── src/
│       ├── app/  App Router pages
│       └── lib/  API client, auth, utilities
├── dna/          Design system + JSON Schemas
│   ├── schemas/  Shared validation contracts
│   ├── conventions/  Naming and code conventions
│   └── outcomes/ WHY behind every rule
└── docs/         Progress tracking + audits
```

### Data Flow (Unidirectional)
```
Next.js App → POST/GET/PATCH → Cloud Functions API → Firestore/GCS
                     ↑
                     └── App NEVER writes to Firestore directly
```

### Key Technologies
- **Backend:** Python 3.11, FastAPI-style Cloud Functions, Pydantic v2
- **Database:** Firestore (australia-southeast1)
- **Storage:** Google Cloud Storage (2 buckets: images, docs)
- **Frontend:** Next.js 16, App Router, TypeScript, Tailwind CSS
- **Auth:** Firebase Auth (Email/Password + custom claims)
- **KYC:** Stripe Identity API
- **Validation:** JSON Schema (dna/schemas/) + Pydantic

---

## 📋 Essential Conventions

### Naming
- **API routes:** `kebab-case` (`create_session.py`, `delete_asset.py`)
- **React components:** `PascalCase` (`HorseForm.tsx`)
- **Firestore collections:** `plural lowercase` (`horses`, `owners`, `hlts`)
- **Firestore fields:** `snake_case` (`foaling_date`, `microchip`)
- **GCS paths:** `{entity_type}/{entity_id}/{uuid}.{ext}`

### API Endpoints
| Entity | Create | Read | Update | Delete |
|--------|--------|------|--------|--------|
| Horses | `POST /horses` | `GET /horses/{microchip}` | `PATCH /horses/{microchip}` | `DELETE /horses/{microchip}` |
| Owners | `POST /owners` | `GET /owners/{id}` | `PATCH /owners/{id}` | `DELETE /owners/{id}` |
| HLTs | `POST /hlts` | `GET /hlts/{id}` | `PATCH /hlts/{id}` | `DELETE /hlts/{id}` |
| Assets | `POST /upload` | `GET /retrieve?...` | — | `DELETE /delete?...` |

### Response Shapes
- **Success (200/201):** Entity object or `{entity, count}` for lists
- **Error (4xx):** `{error: "message"}`
- **Validation:** 400 with field-specific messages

### Primary Keys
- **Horse:** `microchip` (15 digits, natural key from loveracing.nz)
- **All others:** Firestore auto-generated document ID

---

## ⚠️ Common Pitfalls

1. **Never write to Firestore from the app** — All writes must go through `api/` Cloud Functions
2. **Never use horse name as primary key** — Names change; microchips don't
3. **Never skip HLT status validation** — Must follow state machine: `draft → reviewed → publish_ready → published`
4. **Never hardcode GCS paths** — Use entity-based organization: `horse/{microchip}/`
5. **Never define schemas in two places** — JSON Schema in `dna/schemas/` is the single source of truth
6. **Never create bi-directional sync** — Downstream systems are clients only

---

## 📚 Documentation Index

| Document | Purpose | When to Read |
|----------|---------|--------------|
| [`dna/outcomes/WHY.md`](dna/outcomes/WHY.md) | Why each rule exists | Before changing any rule |
| [`GAME_PLAN.md`](GAME_PLAN.md) | 9-checkpoint roadmap | Planning new features |
| [`docs/PROGRESS.md`](docs/PROGRESS.md) | Live build status | Daily standup |
| [`dna/conventions/CONVENTIONS.md`](dna/conventions/CONVENTIONS.md) | Detailed conventions | Writing new code |
| [`dna/schemas/`](dna/schemas/) | JSON Schema contracts | Adding fields to entities |
| [`docs/audit/AUDIT.md`](docs/audit/AUDIT.md) | Quality assessments | Before merging PRs |

---

## 🎯 Current Phase Status

**Phase 1 (MVP):** 🟢 Building
- ✅ Backend: All 3 Cloud Functions deployed
- ✅ Admin UI: All pages complete
- ⏳ Integration testing: In progress

**Next priorities:**
1. Horse detail page with image gallery
2. HLT document generation workflow
3. End-to-end integration tests

---

## Related Documents

- **Plan:** [`GAME_PLAN.md`](GAME_PLAN.md) — 9 checkpoints
- **Current status:** [`docs/PROGRESS.md`](docs/PROGRESS.md) — Live build tracker
- **Overview:** [`docs/BUILD_SUMMARY.md`](docs/BUILD_SUMMARY.md) — High-level summary
- **Blockers:** [`BLOCKERS.md`](BLOCKERS.md) — Resolved issues
- **Audit:** [`docs/audit/AUDIT.md`](docs/audit/AUDIT.md) — Quality assessments