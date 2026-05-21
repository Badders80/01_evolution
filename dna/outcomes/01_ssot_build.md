# Extraction Report: SSOT_Build

**Source:** `/home/evo/workspace/projects/SSOT_Build`
**Date:** 2026-05-19
**Extraction Role:** Lead Cloud Architect — outcome-driven, ignoring current execution methods

---

## Final Artifacts & Deployment Targets

| Artifact | Description | Target |
|----------|-------------|--------|
| Horse/Owner/Trainer/HLT JSON records | Canonical data files for all domain entities | Firestore collections (`horses`, `owners`, `trainers`, `hlts`) |
| HLT Issuance Term Sheet (DOCX) | Legal document generated from HLT record | Cloud Storage bucket → download link |
| Product Disclosure Statement (DOCX) | Regulatory document generated from HLT record | Cloud Storage bucket → download link |
| Syndicate Agreement (DOCX) | Legal document generated from HLT record | Cloud Storage bucket → download link |
| Marketplace payload JSON | Structured payload pushed to Platform for listing | POST to Platform API `/api/marketplace/sync` |
| Vite SPA (local-first) | Authoring UI for horse/owner/trainer/HLT management | Cloud Run or Firebase Hosting (internal admin tool) |

---

## Core Tech Stack & Hard Dependencies

| Dependency | Purpose | Notes |
|------------|---------|-------|
| Vite | Build tool | Production build via `vite build` |
| React 19 | UI library | SPA with route-based views |
| `docx` (npm) | DOCX generation | Used by `generate-pds-doc.ts`, `generate-sa-doc.ts`, `generate-hlt-doc.ts` |
| Zustand | State management | Client-side state store |
| `@evo/dna` | Shared design system | Workspace-linked package (`file:../../../../../workspace/DNA`) |
| `better-sqlite3` | NOT used here (local JSON + localStorage) | Data is JSON files + localStorage, not SQLite |

---

## Environment Variables & Secrets (Keys Only)

| Key | Purpose | Required |
|-----|---------|----------|
| `VITE_API_URL` | Platform API endpoint for marketplace sync | Yes (for publish) |
| `VITE_FIREBASE_CONFIG_*` | Firebase project config (if migrating to Firestore) | Future |
| `DNA_PATH` | Path to shared DNA package | Dev only |

---

## Validation & Testing Commands

| Command | What It Validates |
|---------|-------------------|
| `just check` | TypeScript type-check (`tsc --noEmit`) + production build |
| `npm run build` | Full Vite production build |
| `npm run test:handshake` | HLT handshake integration test |
| `npm run verify:live` | Live mode verification |

---

## Key Business Logic / Pipeline Milestones

1. **Author Horse Record** — Create/edit horse identity anchored by microchip number
2. **Author Owner/Trainer Records** — Independent entities linked by ID (not inlined)
3. **Assemble HLT** — Combine horse identity + commercial lease terms into a single HLT record
4. **Generate 3 Documents** — Term Sheet, PDS, SA all generated from the same canonical HLT record
5. **Human-in-the-Loop Review** — Each document section can be Accepted or Amended before finalization
6. **List HLT** — Change status from `local` → `draft` → `publish_ready` → `published`
7. **Push to Platform** — POST finalized HLT payload to Evolution_Platform API

### Critical Business Rules

- Microchip number is the durable anchor for horse identity (never changes)
- HLT = Horse Identity + Commercial Lease Terms (no HLT without both)
- All 3 documents must generate from the same canonical HLT record
- Human review is mandatory for PDS and SA narrative sections
- Listing status vocabulary must map cleanly to Platform states (`local` → `draft`, `publish_ready` → `coming_soon`, `published` → `open`)
- A horse can exist without an owner or trainer assigned
- Two different owners can list the same horse
- A horse can change trainers over time

### Data Flow (Unidirectional)

```
SSOT_Build → Evolution_Platform (marketplace payload via POST)
SSOT_Build → Evolution_Token (HLT data for tokenization)
SSOT_Build → Evolution_CRM (owner/investor data for SA parties)
```

---

## Migration Debt Watch

| Item | Risk | Recommendation |
|------|------|----------------|
| JSON file + localStorage as "database" | Data loss, no multi-user, no concurrency | Replace with Firestore as canonical store |
| `@evo/dna` workspace link | Breaks if DNA path changes | Package DNA as npm module or copy into project |
| No automated tests for document generation | Silent failures in legal docs | Add Jest tests for DOCX generation |
| Manual publish trigger | No audit trail | Replace with Firestore trigger → Cloud Function |
| `.env` committed to git | Security incident | Move to Secret Manager |