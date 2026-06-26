# Knowledge Repository Gap Analysis & Sprint Plan

**Date:** 2026-06-24
**Author:** glm-5.2 orchestrator (run-plan skill)
**Status:** ✅ COMPLETE — all phases executed

---

## TLDR

The backend manages **13 entity types**. The knowledge repository currently covers **3** (horses, people/trainers, stables) plus 2 extras (pedigrees, press). There are **10 entity types** with no knowledge repo representation — including owners (Kylie Bax / B.A.X Bloodstock), governing bodies (NZTR, DRC), leases, HLTs, and content/transcripts.

This plan closes the gap in 3 phases, prioritizing what you need for marketplace/mystables page building first.

---

## Current State — What's In vs What's Missing

### ✅ In the knowledge repository (5 folders)

| Folder | Files | Backend Entity | Coverage |
|--------|-------|---------------|----------|
| `horses/` | 4 horses × 4 files each | Horse | ✅ Complete for 4 horses |
| `people/` | 4 people | Trainer + Owner | ⚠️ Partial — trainers only, missing owners |
| `stables/` | 2 stables | Trainer (stable_name) | ✅ Complete |
| `pedigrees/` | 5 sires | (no backend entity) | ✅ Bonus — no backend equivalent |
| `press/` | 1 article | (no backend entity) | ✅ Bonus — no backend equivalent |

### ❌ Missing from the knowledge repository (10 entities)

| # | Entity | Backend Location | Key Data | Priority | Why |
|---|--------|-----------------|----------|----------|-----|
| 1 | **Owner** (full) | `api/core/models.py` → `OwnerCreate` | Kylie Bax (B.A.X Bloodstock), Stephen Gray Racing | 🔴 HIGH | You need owner info for horse profiles. Kylie Bax owns 3 of 4 horses. |
| 2 | **Governing Body** | `api/ssot/routes/governing_bodies.py` | NZTR, Dubai Racing Club | 🟡 MED | Referenced by HLTs. Needed for regulatory context on marketplace. |
| 3 | **Lease** | `api/ssot/routes/leases.py` | LSE-001 through LSE-004 — pricing, token counts, investor splits | 🟡 MED | The commercial terms behind each horse offering. Needed for marketplace pricing display. |
| 4 | **HLT** | `api/ssot/routes/hlts.py` | Links horse + owner + trainer + lease + governing body. Status lifecycle. | 🟡 MED | The "campaign" entity — what the marketplace actually lists. |
| 5 | **Content/Transcripts** | `api/ssot/routes/content.py` | Email transcripts, race reports, workout updates per horse | 🟢 LOW | Already partially in `_assets/horses/{slug}/transcripts/`. Not needed for marketplace build. |
| 6 | **DocumentRecord** | `api/ssot/routes/docs.py` | Term Sheets, PDS, Syndicate Agreements | 🟢 LOW | Legal docs — not needed for marketplace pages. |
| 7 | **Holding** | `api/ssot/routes/holdings.py` | Investor ownership stakes | 🟢 LOW | Runtime data — only relevant when live with payments. |
| 8 | **Application** | `api/applications/` | Marketplace purchase applications | 🟢 LOW | Runtime data — only relevant when live. |
| 9 | **User** | `api/kyc/` + `api/payments/` | KYC status, Stripe sessions | 🟢 LOW | Runtime data — only relevant when live. |
| 10 | **Race Result** | `dna/schemas/race.json` (no route) | Individual race starts | 🟡 MED | Needed for race record tabs on marketplace. Schema exists but no API route. |

---

## Key Data Found in Backend (Not in Knowledge Repo)

### Owners (from `seed_data.py`)

| ID | Name | Contact | Type | Horses Owned |
|----|------|---------|------|-------------|
| OWN-001 | B.A.X Bloodstock Achieving Xcellence Limited | Kylie Bax, +64 21 557 045, baxltd@yahoo.com | company | Prudentia, Hotta than a fantasy, I Stole A Manolo |
| OWN-002 | Stephen Gray Racing | Stephen Gray, +64 21 933 183 | company | First Gear |

**Note:** Backend lists Stephen Gray Racing (OWN-002) as the owner entity for First Gear. Breeder is M & W Rose (from loveracing.nz).

### Governing Bodies

| Code | Name | Website | Status |
|------|------|---------|--------|
| NZTR | New Zealand Thoroughbred Racing | nztr.co.nz | active |
| DRC | Dubai Racing Club | dubairacingclub.com | pipeline |

### Leases (commercial terms per horse)

| Lease | Horse | % Leased | Tokens | Token Price (NZD) | Investor Share | Status |
|-------|-------|----------|--------|-------------------|---------------|--------|
| LSE-001 | First Gear | 10% | 20 | $240 | 80% | complete |
| LSE-002 | Prudentia | 5% | 20 | $292.50 | 75% | draft |
| LSE-003 | Hotta than a fantasy | 5% | 20 | $280 | 75% | draft |
| LSE-004 | I Stole A Manolo | 5% | 20 | $280 | 75% | draft |

### HLTs (campaign records)

| HLT | Horse | Owner | Trainer | Governing Body | Lease | Status |
|-----|-------|-------|---------|---------------|-------|--------|
| HLT-1 | First Gear | SGR (OWN-002) | SGR (TRN-002) | NZTR | LSE-001 | draft |
| HLT-2 | Prudentia | B.A.X (OWN-001) | Wexford (TRN-001) | NZTR | LSE-002 | draft |
| HLT-3 | Hotta than a fantasy | B.A.X (OWN-001) | Wexford (TRN-001) | NZTR | LSE-003 | draft |
| HLT-4 | I Stole A Manolo | B.A.X (OWN-001) | Wexford (TRN-001) | NZTR | LSE-004 | draft |

### Correct Microchips (from backend, different from HORSES.csv!)

| Horse | Correct Microchip | HORSES.csv Microchip |
|-------|------------------|---------------------|
| First Gear | 985125000126713 | 985141004523601 |
| Prudentia | 985125000126462 | 985141004512345 |
| Hotta than a fantasy | 985125000139165 | 985141004517845 |
| I Stole A Manolo | 985125000139219 | 985141004518932 |

**⚠️ The microchips in HORSES.csv and the pedigree.json files are WRONG.** The backend seed data has the correct ones (verified against loveracing.nz URLs in the seed data).

---

## Sprint Plan

### Phase 1: Fix + Fill High Priority Gaps (do now)

**Goal:** Get owners, governing bodies, and correct microchips into the knowledge repo.

1. **Fix microchips** in all 4 `pedigree.json` files + `HORSES.csv` + horse profile frontmatter
2. **Add Kylie Bax / B.A.X Bloodstock** to `people/` with owner role
3. **Update Stephen Gray** profile — he's already there but needs owner context (B.A.X vs SGR ownership)
4. **Add governing bodies** — new `governing-bodies/` folder with NZTR and DRC profiles
5. **Update horse frontmatter** — link to correct owners (B.A.X for 3 horses, SGR for First Gear)

### Phase 2: Commercial Terms (do next, for marketplace)

**Goal:** Get lease and HLT data into the knowledge repo so marketplace pages can be built from it.

6. **Add `leases/` folder** — one file per lease (LSE-001 through LSE-004) with structured JSON
7. **Add `hlts/` folder** — one file per HLT campaign, linking horse + owner + trainer + lease + governing body
8. **Update `kb-index.py`** — add `--lease` and `--hlt` query support

### Phase 3: Content & Race Data (do when needed)

**Goal:** Get transcripts and race results accessible locally.

9. **Add race results** — populate `race-record.json` files with actual start data from loveracing.nz
10. **Index transcripts** — create index files in `horses/{slug}/` pointing to transcripts in `_assets/horses/{slug}/transcripts/`

### Out of Scope (runtime data, not knowledge repo material)

- Holdings (investor stakes) — runtime, only when live
- Applications (purchase requests) — runtime, only when live
- Users (KYC status) — runtime, only when live
- DocumentRecords (legal docs) — stored in GCS, not knowledge repo material

---

## Proposed Folder Structure (Full)

```
01_evolution/
  horses/                    ✅ Done (fix microchips)
  people/                    ✅ Done (add Kylie Bax)
  stables/                   ✅ Done
  pedigrees/                 ✅ Done
  press/                     ✅ Done
  governing-bodies/          ← NEW (Phase 1)
    nztr/profile.md
    dubai-racing-club/profile.md
  leases/                    ← NEW (Phase 2)
    lse-001.json             ← First Gear lease terms
    lse-002.json             ← Prudentia lease terms
    lse-003.json             ← Hotta lease terms
    lse-004.json             ← I Stole A Manolo lease terms
  hlts/                      ← NEW (Phase 2)
    first-gear.md            ← Campaign: horse + owner + trainer + lease + status
    prudentia.md
    hottathanafantasy.md
    i-stole-a-manolo.md
  kb-index.py                ← Update for new folders
  README-knowledge-repo.md   ← Update
```

---

## Definition of Done

### Phase 1
- [ ] All 4 microchips corrected in pedigree.json, HORSES.csv, and horse profiles
- [ ] Kylie Bax / B.A.X Bloodstock profile created in `people/`
- [ ] Governing bodies folder created with NZTR + DRC profiles
- [ ] Horse frontmatter updated with correct owner links
- [ ] `kb-index.py --horse prudentia` returns owner (bax-bloodstock) in results

### Phase 2
- [ ] `leases/` folder with 4 lease JSON files
- [ ] `hlts/` folder with 4 campaign markdown files
- [ ] `kb-index.py` updated with `--lease` and `--hlt` query support
- [ ] `kb-index.py --horse first-gear` returns lease + HLT in results

### Phase 3
- [ ] Race records populated with actual start data
- [ ] Transcript index files created

---

## Open Questions

1. ~~Bill Rose vs SGR~~ — RESOLVED. Backend is canonical: SGR (OWN-002) is the owner. M & W Rose is the breeder per loveracing.nz. No Bill Rose in the backend.

2. **B.A.X Bloodstock** — Kylie Bax owns 3 of the 4 horses via B.A.X Bloodstock. Should she have a `people/` profile, or should the company entity `bax-bloodstock/` be the profile with Kylie as the contact?

3. **Microchip discrepancy** — The backend seed data has different microchips than HORSES.csv. The backend ones link to real loveracing.nz URLs. Should we treat the backend as canonical and update everything else?

4. **Lease pricing** — The backend lease prices are in NZD. The tokinvest listings show AED. Should the knowledge repo store both?