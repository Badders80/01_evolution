# Evolution — Conventions

**Version:** 1.0
**Last Updated:** 2026-05-19

---

## Naming Conventions

### Files and Folders

| Type | Convention | Example |
|------|-----------|---------|
| API routes | kebab-case | `create_session.py`, `delete_asset.py` |
| React components | PascalCase | `HorseForm.tsx`, `AssetUpload.tsx` |
| React pages | kebab-case folders | `admin/horses/new/page.tsx` |
| JSON Schemas | snake_case | `horse.json`, `owner.json` |
| Pydantic models | PascalCase classes | `HorseCreate`, `OwnerUpdate` |
| Firestore collections | plural lowercase | `horses`, `owners`, `trainers`, `hlts`, `assets` |
| GCS paths | `{entity_type}/{entity_id}/{uuid}.{ext}` | `horse/985125000126462/a1b2c3.jpg` |

### Code

| Language | Convention | Notes |
|----------|-----------|-------|
| Python | PEP 8, snake_case functions | `create_horse()`, `get_horse_by_microchip()` |
| TypeScript | camelCase functions, PascalCase types | `createHorse()`, `HorseCreate` |
| CSS | Tailwind utility classes | No custom CSS files |
| Firestore fields | snake_case | `foaling_date`, `sire_name`, `life_number` |

## API Conventions

### URL Patterns

| Entity | List | Get | Create | Update | Delete |
|--------|------|-----|--------|--------|--------|
| Horses | `GET /horses` | `GET /horses/{microchip}` | `POST /horses` | `PATCH /horses/{microchip}` | `DELETE /horses/{microchip}` |
| Owners | `GET /owners` | `GET /owners/{id}` | `POST /owners` | `PATCH /owners/{id}` | `DELETE /owners/{id}` |
| Trainers | `GET /trainers` | `GET /trainers/{id}` | `POST /trainers` | `PATCH /trainers/{id}` | `DELETE /trainers/{id}` |
| HLTs | `GET /hlts` | `GET /hlts/{id}` | `POST /hlts` | `PATCH /hlts/{id}` | `DELETE /hlts/{id}` |
| Assets | — | `GET /retrieve?entity_type=...&entity_id=...` | `POST /upload` | — | `DELETE /delete?asset_id=...` |
| KYC | — | — | `POST /create-session` | — | — |

### Response Shapes

**Success:**
```json
{
  "id": "...",
  "microchip": "985125000126462",
  ...
}
```

**List:**
```json
{
  "horses": [...],
  "count": 42
}
```

**Error:**
```json
{
  "error": "Microchip must be exactly 15 digits"
}
```

### HTTP Status Codes

| Code | Usage |
|------|-------|
| 200 | Success (get, update) |
| 201 | Created |
| 400 | Validation error |
| 404 | Not found |
| 405 | Method not allowed |
| 409 | Conflict (duplicate microchip) |

## Data Conventions

### Primary Keys

| Entity | Primary Key | Format |
|--------|------------|--------|
| Horse | `microchip` | 15 digits, queried by Firestore `where` clause |
| Owner | `id` (auto-generated) | Firestore document ID |
| Trainer | `id` (auto-generated) | Firestore document ID |
| HLT | `id` (auto-generated) | Firestore document ID |
| Asset | `id` (auto-generated) | Firestore document ID |
| User | `id` (Firebase Auth UID) | Firebase Auth UID |

### Timestamps

All entities have `created_at` and `updated_at` fields using `SERVER_TIMESTAMP`.

### Status Fields

HLT status follows a strict state machine:
```
draft → reviewed → publish_ready → published
  ↑         ↓          ↓              ↓
  └─────────┘          └──────────────┘
```

Step 1 only uses `draft` and `reviewed`.

## Security Conventions

1. **API is the only writer.** The Next.js app never writes to Firestore directly.
2. **Firebase Auth + custom claims.** Roles: `admin`, `investor`, `viewer`.
3. **Stripe Identity for KYC.** Investors must be verified before investing.
   → **Full spec:** [`dna/conventions/STRIPE.md`](STRIPE.md)
4. **Cloud Functions validate all input.** Pydantic models enforce schema.
5. **GCS buckets are private.** Signed URLs for asset access (Step 2).

## Deployment Conventions

| Component | Platform | Region |
|-----------|----------|--------|
| Firestore | Google Cloud | australia-southeast1 |
| Cloud Functions | Google Cloud | australia-southeast1 |
| Cloud Storage | Google Cloud | australia-southeast1 |
| Next.js | Vercel (or Cloud Run) | — |

## Git Conventions

- **Branch naming:** `feature/{description}`, `fix/{description}`
- **Commit messages:** Conventional commits (`feat:`, `fix:`, `docs:`, `chore:`)
- **PR titles:** Descriptive, reference the checkpoint number