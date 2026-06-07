# Racing Data — Firestore Schema

## Overview

Racing data is stored in a subcollection under each horse document:

```
horses/{microchip}/races/{race_id}
horses/{microchip}/summary/summary
```

Where `microchip` is the 15-digit NZ microchip number (the durable anchor).

---

## RaceResult Document: `horses/{microchip}/races/{race_id}`

### Document ID (race_id)

**Composite key for idempotent upserts:**
```
{race_date}_{venue}_{race_name_slug}
```

- `race_date`: ISO format YYYY-MM-DD
- `venue`: Venue code (e.g., TE_RAPA, ELLE, WAIK)
- `race_name_slug`: Lowercase, alphanumeric + hyphens only, max 50 chars

**Example:** `2024-11-09_TE_RAPA_maiden-1200`

This ensures re-scraping the same horse won't create duplicates.

### Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| horse_microchip | string | ✅ | 15-digit microchip (matches parent doc) |
| loveracing_id | integer | ✅ | HorseID on loveracing.nz |
| race_date | string (date) | ✅ | ISO format: YYYY-MM-DD |
| venue | string | ✅ | Race track / venue |
| race_name | string | ✅ | Official race name |
| race_class | string | | Class or grade (Maiden, Open, Group 3, etc.) |
| distance_metres | integer | | Race distance in metres |
| field_size | integer | | Number of starters |
| barrier | integer | | Barrier draw number |
| jockey | string | | Jockey name |
| trainer | string | | Trainer name at time of race |
| finish_position | integer | ✅ | 1 = win, 0 = unplaced (U) |
| prize_money_nzd | integer | ✅ | Prize money in NZD **cents** (e.g., 1250000 = $12,500.00) |
| starting_price | string | | Starting price (e.g., "$8.20") |
| rating | integer | | Official rating at time of race |
| weight | number | | Weight carried in kg |
| gear | string | | Raceday gear |
| stake_type | string | ✅ | Enum: "win", "place", "unplaced" |
| source_url | string | | Direct link to race entry on loveracing.nz |
| scraped_at | timestamp | | When this record was scraped |
| scraper_version | string | | Version for traceability (e.g., "scraper/loveracing/v0.1") |
| raw_html_checksum | string | | SHA256 of raw HTML for change detection |

---

## HorseRacingSummary Document: `horses/{microchip}/summary/summary`

Single document (always ID = "summary") with computed aggregates.

### Fields

| Field | Type | Description |
|-------|------|-------------|
| horse_microchip | string | 15-digit microchip |
| loveracing_id | integer | HorseID on loveracing.nz |
| total_starts | integer | Career starts count |
| total_wins | integer | Career wins count |
| total_places | integer | Career 2nd + 3rd count |
| total_earnings_nzd | integer | Career total in NZD **cents** |
| earnings_by_age | map<string, integer> | Earnings by age at race (keys: "2", "3", "4", etc.) |
| earnings_by_class | map<string, integer> | Earnings by race class |
| first_start_date | string (date) | First race date (ISO) |
| last_start_date | string (date) | Most recent race date (ISO) |
| computed_at | timestamp | When summary was computed |

---

## Horse Document: `horses/{microchip}`

The parent horse document (managed by `api/ssot/`) includes these racing-relevant fields:

| Field | Type | Description |
|-------|------|-------------|
| microchip | string | 15-digit (document ID) |
| loveracing_id | integer | For URL construction |
| name | string | Registered name |
| foaling_date | string (date) | Date of birth |
| sex | string | colt/filly/gelding/mare/stallion/horse |
| colour | string | Bay, Chestnut, etc. |
| trainer | string | Current trainer (from breeding page) |

---

## Indexes Required

### Composite Indexes for `horses/{microchip}/races`

1. **Query by horse + date range (DESC)**
   - Fields: `horse_microchip` (ASC), `race_date` (DESC)
   - Used by: `read_race_results()` with pagination

2. **Query by horse + stake_type**
   - Fields: `horse_microchip` (ASC), `stake_type` (ASC), `race_date` (DESC)
   - Used by: Filtering wins/places/unplaced

---

## Security Rules

```javascript
match /horses/{microchip}/races/{raceId} {
  allow read: if request.auth != null;
  allow write: if request.auth != null && request.auth.token.admin == true;
}

match /horses/{microchip}/summary/{docId} {
  allow read: if request.auth != null;
  allow write: if request.auth != null && request.auth.token.admin == true;
}
```

---

## Migration Notes

- `race_id` uses composite key for idempotency — re-scraping overwrites same document
- `prize_money_nzd` stored as **cents** (integer) to avoid floating-point issues
- `scraper_version` enables tracing data lineage when schema evolves
- `raw_html_checksum` enables detecting source HTML changes for re-scrape decisions