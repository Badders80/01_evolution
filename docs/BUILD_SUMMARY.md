# Evolution Stables — Build Summary

**Date:** 2026-05-20
**Status:** Phase 1 MVP built, Sprint 2 ✅ Complete, persistent navbar live

> **This is the map.** What the project is, what exists, the rules.
> For session-by-session progress, see [PROGRESS.md](PROGRESS.md).

---

## What We're Building

A platform for fractional racehorse ownership in New Zealand. Investors browse horses → complete KYC → buy shares → track in MyStable.

**The rosetta stone:** Every NZ thoroughbred has a Stud Book page on loveracing.nz. We anchor every horse record to its microchip (15 digits, never changes) and enrich from that page.

Example: [Prudentia (NZ) 2021](https://loveracing.nz/Breeding/427416/Prudentia-NZ-2021.aspx) gives us microchip `985125000126462`, life number `NZ00427416`, sire PROISIR, dam LITTLE BIT IRISH, brands, breeder — all verified data.

---

## Build Philosophy

**Old approach:** Decide all outcomes upfront → build everything to fit → test at the end.
**New approach:** Start from the data → build one slice → verify it works → add the next.

Each slice must produce something you can verify. No slice depends on a future slice.

---

## What Exists Now

### API Layer (Python Cloud Functions)

| Function | Routes | Status |
|----------|--------|--------|
| **SSOT** | `/horses`, `/owners`, `/trainers`, `/hlts`, `/docs` | ✅ Complete |
| **Assets** | `/upload`, `/bulk-upload`, `/retrieve`, `/delete` | ✅ Complete |
| **KYC** | `/create-session`, `/webhook` | ✅ Complete |

Key design: `api/` is the **only** writer to Firestore. The app never writes directly.

### Data Model (Firestore)

| Collection | Primary Key | Key Design Decision |
|-------------|------------|-------------------|
| `horses` | `microchip` (15 digits) | Anchored to loveracing.nz, never changes |
| `owners` | `id` (auto) | individual/syndicate/corporate |
| `trainers` | `id` (auto) | NZTR-licensed |
| `hlts` | `id` (auto) | Status state machine: draft → reviewed → publish_ready → published |
| `assets` | `id` (auto) | Entity-anchored: horse/owner/trainer/hlt/marketplace. Context-rich naming + auto-tagging |
| `users` | Firebase Auth UID | KYC status tracked |

### Next.js App (`02_website/` — Frontend Only)

| Route | Purpose | Status |
|-------|---------|--------|
| `(public)/` | Home, About, Press | ✅ Built |
| `admin/` | Dashboard with live stats, KYC banner | ✅ Built |
| `admin/horses/` | List + new form | ✅ Built |
| `admin/horses/new` | **2-step registration** with loveracing.nz import | ✅ Built |
| `admin/horses/[microchip]/` | Horse detail with image gallery | ✅ Built |
| `admin/owners/` | List + create | ✅ Built |
| `admin/trainers/` | List + create | ✅ Built |
| `admin/hlts/` | List + create + review | ✅ Built |
| `admin/assets/` | Content repository + browse | ✅ Built |
| `admin/assets/upload/` | Bulk upload (drag & drop, entity-anchored) | ✅ Built |
| `admin/website/press/` | Press article CMS placeholder | ✅ Built |
| `admin/website/faq/` | FAQ CMS placeholder | ✅ Built |
| `auth/login` | Firebase Auth (email + Google) | ✅ Built |
| `auth/verify` | Stripe KYC flow | ✅ Built |

> **Note:** Admin pages were originally built in `01_evolution/app/` (architectural drift) and moved to `02_website/src/app/admin/` on 2026-05-20. `01_evolution` is backend-only.

### DNA (Design System)

| File | Purpose |
|------|---------|
| `dna/schemas/horse.json` | JSON Schema for horse record |
| `dna/schemas/owner.json` | JSON Schema for owner |
| `dna/schemas/trainer.json` | JSON Schema for trainer |
| `dna/schemas/hlt.json` | JSON Schema for HLT (with status lifecycle) |
| `dna/schemas/asset.json` | JSON Schema for assets |
| `dna/brand/BRAND_SYSTEM.md` | Colors (#d4a964 gold, #121212 black), typography, spacing |
| `dna/brand/VOICE_SYSTEM.md` | Tone, terminology, writing rules |
| `dna/conventions/CONVENTIONS.md` | Naming, API patterns, security rules |

---

## Architecture Rules

1. **Microchip is the durable anchor.** Every horse is identified by its 15-digit microchip from loveracing.nz.
2. **`api/` is the only data writer.** The app never writes to Firestore directly.
3. **HLT status is a state machine.** `draft → reviewed → publish_ready → published`. Step 1 only uses `draft` and `reviewed`.
4. **Assets are organized by entity.** `horse/{microchip}/` in GCS.
5. **DNA schemas are the contract.** Pydantic models and React forms both validate against the same JSON Schemas.
6. **No bi-directional sync.** Downstream systems are clients of the SSOT API.
7. **Content is entity-anchored and context-rich.** Every asset belongs to a horse (by microchip). Filenames encode horse, date, and context. Tags auto-generate from horse, owner (via HLT), trainer, location, and context.

---

## Human Handoff Points

These require credentials I don't have:

| Blocker | What's Needed |
|---------|--------------|
| GCP Project | `gcloud auth login` + create Firestore + Storage buckets |
| Stripe Account | `STRIPE_SECRET_KEY`, `STRIPE_PUBLISHABLE_KEY`, `STRIPE_WEBHOOK_SECRET` |
| Firebase Auth | `FIREBASE_CONFIG` JSON |
| Deployment | `gcloud functions deploy` for each function |

---

## Related Documents

- **Current status:** [`PROGRESS.md`](PROGRESS.md) — Session tracker, what's next, architecture status
- **Plan:** [`GAME_PLAN.md`](../GAME_PLAN.md) — 9 checkpoints
- **Blockers:** [`BLOCKERS.md`](../BLOCKERS.md) — Resolved issues
- **Laws:** [`AGENTS.md`](../AGENTS.md) — Core architecture rules
- **Audit:** [`audit/AUDIT.md`](audit/AUDIT.md) — Quality assessments
- **Logs:** [`logs/`](logs/) — Daily session notes