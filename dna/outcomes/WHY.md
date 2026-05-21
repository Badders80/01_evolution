# WHY — Grounding Every Decision in the Problem It Solves

**Date:** 2026-05-19
**Purpose:** Every architecture rule in this build exists because the old workspace broke without it. This document connects each rule to the failure it prevents, so no future agent (or future you) can "simplify" it back into the same hole.

---

## How to Use This Document

1. Before adding a new feature, check if your approach violates any rule below.
2. Before removing or "simplifying" a rule, read the **Anti-pattern** section — that's what happens if you break it.
3. If you're unsure why something exists, find the connected outcome file for the full context.

---

## Law 1: Microchip is the durable anchor

**Rule:** Every horse is identified by its 15-digit microchip from loveracing.nz. This never changes.

**Problem it solves:** The old SSOT_Build had no stable identifier. Horses were identified by name (which changes — horses get renamed), by ID (which was auto-generated and meaningless), or by breeder reference (which was inconsistent). The result: duplicate horse records, data drift between projects, and no way to verify a horse's identity against an external source.

**Anti-pattern to avoid:** Never use horse name as a primary key. Never generate a synthetic ID when a natural key exists. Never allow a horse record without a microchip.

**What happens if you break it:** Duplicate records. A horse appears twice with slightly different data. Two projects disagree on which record is canonical. You spend hours reconciling instead of building.

**Connected outcome:** `01_ssot_build.md` — the old build used JSON files + localStorage with no durable key.

---

## Law 2: `api/` is the only data writer

**Rule:** The app never writes to Firestore directly. All writes go through the Cloud Functions API.

**Problem it solves:** The old workspace had 5 projects (SSOT, Platform, Token, Content, Studio) each writing to their own SQLite databases with no sync mechanism. Data drifted constantly. A horse updated in SSOT didn't update in Platform. An owner created in Token didn't appear in CRM. The "solution" was manual sync scripts that broke regularly.

**Anti-pattern to avoid:** Never add a second writer "for convenience." Never let the app bypass the API to write directly to Firestore. Never create a Cloud Function that writes to another project's collections.

**What happens if you break it:** Two writers disagree on the truth. You build reconciliation scripts. The reconciliation scripts break. You build reconciliation for the reconciliation. This is how the old workspace died.

**Connected outcome:** `00_migration_advisor_summary.md` — the entire "Debt & Drift" section is about this problem. Also `12_shared_infrastructure.md` — the cross-project dependency map shows how many projects were writing to their own stores.

---

## Law 3: HLT status is a state machine

**Rule:** `draft → reviewed → publish_ready → published`. Step 1 only uses `draft` and `reviewed`.

**Problem it solves:** The old SSOT_Build had no publish workflow. Documents went straight from creation to "live" with no review gate. The status field was `local → draft → publish_ready → published` but there was no enforcement — any status could be set at any time. The result: unreviewed legal documents (Term Sheets, PDS, Syndicate Agreements) could be published to the marketplace.

**Anti-pattern to avoid:** Never allow arbitrary status transitions. Never skip the review step. Never set status directly — always use the transition API.

**What happens if you break it:** An unreviewed PDS with incorrect financial figures gets published. Investors make decisions based on wrong data. Regulatory liability.

**Connected outcome:** `01_ssot_build.md` — the old build had "Human-in-the-Loop Review" as a milestone but no enforcement mechanism. Also `05_token.md` — the old Token project expected to receive "published" HLTs but had no way to verify they'd been reviewed.

---

## Law 4: Assets are organized by entity

**Rule:** `horse/{microchip}/` in GCS. Every asset knows what entity it belongs to via `entityType` + `entityId`.

**Problem it solves:** The old Evolution_Content project dumped everything into flat buckets with no structure. Images, videos, audio, documents — all in one place with no organization. The result: no way to find all images for a specific horse, no way to generate thumbnails at scale, no way to clean up assets when a horse record was deleted.

**Anti-pattern to avoid:** Never create a flat asset bucket. Never store assets without entity metadata. Never hardcode a path like `images/horses/` — use the entity system.

**What happens if you break it:** You can't answer "show me all images for horse X" without scanning the entire bucket. Thumbnails don't get cleaned up. Storage costs grow without bound.

**Connected outcome:** `02_content.md` — the old project had `media/` as a flat directory with no structure. Also `03_studio.md` — Studio generated images with no entity linkage.

---

## Law 5: DNA schemas are the contract

**Rule:** Pydantic models and React forms both validate against the same JSON Schemas in `dna/schemas/`.

**Problem it solves:** The old workspace had no shared schema. SSOT_Build defined horse fields in TypeScript. Platform defined them differently in Zod. Token defined them differently again in Solidity. The result: field names didn't match, required fields were different, and data that passed validation in one project failed in another.

**Anti-pattern to avoid:** Never define a field in a React form without checking the JSON Schema first. Never add a field to a Pydantic model without updating the JSON Schema. Never assume two projects agree on field names.

**What happens if you break it:** The API accepts a field the form doesn't send. The form sends a field the API doesn't expect. You spend hours debugging "why is this field null?" when the answer is: two different schemas.

**Connected outcome:** `12_shared_infrastructure.md` — the old `@evo/dna` package was a workspace link (`file:../../../../../workspace/DNA`) that broke if the path changed. Also `01_ssot_build.md` — the old build had no JSON Schema, just TypeScript interfaces.

---

## Law 6: No bi-directional sync

**Rule:** Downstream systems are clients of the SSOT API. They POST updates; they don't sync back.

**Problem it solves:** The old architecture had Platform pulling from SSOT and SSOT pulling from Platform. Content pushed to Platform and Platform pushed status back to Content. The result: infinite sync loops, race conditions, and data that was "correct" in one direction but wrong in the other.

**Anti-pattern to avoid:** Never create a webhook that writes back to the source. Never add a "sync" endpoint that merges data from two directions. Never let a consumer update the producer's data.

**What happens if you break it:** Change A triggers sync to B. B processes A and sends confirmation back to A. A interprets the confirmation as a new change. B processes the "new" change. This is literally how the old Platform and SSOT got into an infinite loop.

**Connected outcome:** `04_platform.md` — the old Platform had "SSOT Sync" as a feature, meaning it received data from SSOT. But it also had a file watcher that tried to sync back. Also `01_ssot_build.md` — the old build had "Push to Platform" as a manual step, which meant Platform could also push back.

---

## What's NOT in Step 1 (and why)

These outcomes exist in the extraction reports but are deliberately deferred:

| Outcome | Where It's Documented | Why It's Deferred |
|---------|----------------------|-------------------|
| Content scraping pipeline | `02_content.md` | Step 3 — we need the horse data first |
| Video/image production | `03_studio.md` | Step 3 — we need assets to produce content from |
| Marketplace listings | `04_platform.md` | Step 2 — we need reviewed HLTs first |
| Share purchase / payments | `05_token.md` | Step 2 — we need KYC-verified investors first |
| GST / financial processing | `06_ops.md` | Step 4 — we need transactions to process first |
| Lead tracking / CRM | `07_crm.md` | Step 4 — we need a public site to capture leads from first |
| Agent orchestration | `09_dev.md` | Step 3 — the agent layer was a stub in the old build too |
| Regulatory compliance docs | `10_nzes.md` | Reference only — the HLT status machine handles this |
| Market research / syndicator data | `11_own.md` | Reference only — informs pricing in Step 2 |

---

## The Old Workspace at a Glance

| Project | What It Tried to Do | What Actually Worked | What Failed |
|---------|---------------------|---------------------|-------------|
| SSOT_Build | Author horse/owner/trainer/HLT records, generate legal docs | Horse identity concept, HLT assembly, doc generation | No stable key, JSON+localStorage, no publish enforcement |
| Evolution_Content | Scrape NZ racing content, catalog, serve | Scraping scripts worked, GCS uploads worked | SQLite, no tests, flat asset storage, dual AI clients |
| Evolution_Studio | Produce videos, images, investor updates | Kingmaker video pipeline worked | Multiple AI providers, manual git push, no tests |
| Evolution_Platform | Public website + marketplace + investor portal | Best test coverage in the ecosystem | SQLite, NextAuth v4, 108MB unoptimized public/ dir |
| Evolution_Token | Share purchase + KYC + smart contracts | Smart contract compiled, Stripe integration started | SQLite, wallet-only auth, separate repo from Platform |
| Evolution_Ops | GST reports, bank reconciliation, payroll | GST calculation scripts worked | No tests, local-only, no cloud deployment |
| Evolution_CRM | Lead tracking, investor communication | Architecture docs only | No code exists |
| Evolution_CTO | Cross-project dashboard | JSON file aggregation | Not a deployable service |
| Evolution_Dev | Agent orchestration | dispatch.js loop concept | state-api was a stub, no retry, no verification |
| Evolution_NZES | Regulatory analysis | Document research only | No code |
| Evolution_Own | Market research, syndicator data | Scraping scripts | No structured store |
| Shared Infra | Cross-project rules, DNA | PROJECTS_RULES, DNA concept | Symlinked .env, no CI/CD, no security rules |

---

## File Index

| File | What It Contains |
|------|------------------|
| `00_migration_advisor_summary.md` | Debt & drift watch — the master list of what was wrong |
| `01_ssot_build.md` | Horse/owner/trainer/HLT authoring — the core data layer |
| `02_content.md` | Content scraping, cataloging, serving |
| `03_studio.md` | Video/image production, investor updates |
| `04_platform.md` | Public website, marketplace, investor portal |
| `05_token.md` | Share purchase, KYC, smart contracts |
| `06_ops.md` | GST, banking, payroll |
| `07_crm.md` | Lead tracking, investor communication |
| `08_cto.md` | Cross-project dashboard |
| `09_dev.md` | Agent orchestration infrastructure |
| `10_nzes.md` | Regulatory analysis (FMA, NZTR) |
| `11_own.md` | Market research, syndicator data |
| `12_shared_infrastructure.md` | Cross-project dependencies, DNA, secrets |
| `13_step1_mvp.md` | What we're actually building in Step 1 |
| `14_step1_setup.md` | The minimal technical setup for Step 1 |
| `15_build_status.md` | Live tracker of what's built vs planned |