# Sprint One: Horse Media Console + Data Sync

**Status:** 🟡 IN PROGRESS  
**Date Created:** 2026-06-10  
**Priority:** 🔴 ACTIVE  
**Estimated Effort:** 3-4 hours  

---

## Executive Summary

**Trigger:** 4 Wexford horses need to be added to Mission Control. Prudentia has 4 transcripts stored locally that need to be synced to Firestore. The horse detail view needs a media console to browse transcripts and images.

**Goal:** Complete horse intake, fix data pipeline, build media console UI.

**Success Criteria:**
- [ ] 4 horses in Mission Control with Loveracing data
- [ ] SSOT API accessible from email ingest pipeline
- [ ] All Prudentia transcripts in Firestore with real IDs
- [ ] Horse detail page shows media console (transcripts + images)
- [ ] 128/128 tests still passing

---

## Phase 1: Horse Intake

### Horses to Add

| # | Name | Microchip | Life Number | Loveracing ID | Rating |
|---|------|-----------|-------------|---------------|--------|
| 1 | Prudentia (NZ) 2021 | 985125000126462 | NZ00427416 | 427416 | 75 |
| 2 | Hottathanafantasy (NZ) 2023 | TBD | TBD | 452052 | — |
| 3 | I-Stole-A-Manolo (NZ) 2023 | TBD | TBD | 451442 | — |
| 4 | First-Gear (NZ) 2021 | TBD | TBD | 428364 | — |

**Actions:**
- [ ] Scrape Loveracing for microchip, life number, breeding data
- [ ] Insert into Mission Control SQLite database
- [ ] Verify horses appear in Mission Control UI

---

## Phase 2: Data Pipeline Fix

### SSOT API 403

**Problem:** Email ingest pipeline calls Cloud Functions without auth headers → 403.

**Fix:** Add service account bypass on deployed Cloud Functions.

**User action required:**
1. Go to GCP Console → Cloud Functions
2. For each function (ssot, assets, kyc):
   - Click function → Permissions tab
   - Add principal: `evolution-engine@appspot.gserviceaccount.com`
   - Role: `Cloud Functions Invoker`
   - Save

### SQLite Schema Fix

**Problem:** `trigger_imap.py` queries `horse_name` column but `emails` table doesn't have it.

**Fix:** Add `horse_name`, `asset_id`, `content_id` columns to `emails` table.

### Transcript Dedup

**Problem:** Filenames inconsistent (`transcript_: Prudentia` vs `transcript_Prudentia`).

**Fix:** Normalize to `transcript_{horse}_{date}.json`.

---

## Phase 3: Media Console

### Backend Endpoint

`GET /api/horses/{microchip}/media`

Returns:
```json
{
  "horse": { "name": "Prudentia (NZ) 2021", "microchip": "..." },
  "transcripts": [
    { "id": "...", "date": "2026-06-10", "speakers": ["Andrew Scott", "Lance O'Sullivan"], "preview": "Won't run Saturday..." }
  ],
  "images": []
}
```

### Frontend View

When clicking a horse in Mission Control, the detail view shows:
- Horse info (name, microchip, rating, breeding)
- Media section with transcript list (date, speakers, preview, play/transcript buttons)
- Image section (grid of thumbnails)

---

## Phase 4: Verification

- [ ] 128/128 tests pass
- [ ] Mission Control UI loads and shows 4 horses
- [ ] Horse detail view shows media console
- [ ] Sign-in/out still works
- [ ] No new debt introduced
