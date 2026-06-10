# Blockers & Human Handoff Points

## 1. ~~GCP Project Setup~~ ✅ RESOLVED
- Firestore database exists in `australia-southeast1`
- Storage buckets created: `gs://evolution-horse-images`, `gs://evolution-horse-docs`
- ADC credentials configured at `~/.config/gcloud/application_default_credentials.json`
- Project: `evolution-engine` (ID: 851430309148)

## 2. ~~Stripe Account Setup~~ ✅ RESOLVED
- Stripe CLI authenticated for Evolution Stables sandbox (`acct_1TLJdYJNM3QjvBY1`)
- Publishable key set in `app/.env.local`
- Secret key + webhook signing secret set in `api/.env.api`
- **Note:** `whsec_` secret is from `stripe listen` — for production, create a webhook endpoint in Stripe Dashboard

## 3. ~~Firebase Auth Setup~~ ✅ RESOLVED
- Firebase project added to `evolution-engine`
- Web app created: `1:851430309148:web:41dd7c7e2be68539beced9`
- Config pre-filled in `app/.env.local` as `NEXT_PUBLIC_FIREBASE_CONFIG`
- Identity Toolkit API enabled
- **⚠️ One manual step:** Enable Email/Password sign-in at https://console.firebase.google.com/project/evolution-engine/authentication → Sign-in method → Enable Email/Password

## 4. ~~Cloud Function Deployment~~ ✅ RESOLVED
All 3 Cloud Functions deployed to `australia-southeast1` (1st gen):

| Function | URL | Status |
|----------|-----|--------|
| **SSOT** | `https://australia-southeast1-evolution-engine.cloudfunctions.net/ssot` | ✅ ACTIVE |
| **Assets** | `https://australia-southeast1-evolution-engine.cloudfunctions.net/assets` | ✅ ACTIVE |
| **KYC** | `https://australia-southeast1-evolution-engine.cloudfunctions.net/kyc` | ✅ ACTIVE |

**Note:** KYC is not publicly accessible (requires authentication for webhook security).

---

## 🔴 NEW: Sprint Zero Blockers (2026-06-10)

### 5. Model Fragmentation — ✅ RESOLVED

**Issue:** 3+ conflicting model definitions causing import errors and schema drift.

**Resolution:**
- ✅ Created `api/core/models.py` as single source of truth
- ✅ Deleted `api/models/`, `api/ssot/models/`, `api/admin/models.py`
- ✅ Updated all imports across 20+ files
- ✅ All models import successfully

**Status:** ✅ RESOLVED — See [`docs/sprints/S00_foundation_security.md`](docs/sprints/S00_foundation_security.md)

### 6. Broken Test Infrastructure — ✅ RESOLVED

**Issue:** 4/7 test files fail at import time (missing Flask, requests, model imports)

**Resolution:**
- ✅ Added `Flask`, `Flask-CORS`, `requests`, `pytest`, `pytest-flask` to `api/requirements.txt`
- ✅ Fixed all model imports in tests
- ⏳ **Next:** Run full test suite to verify

**Status:** 🟡 READY TO VERIFY — Pending `pytest` execution

### 7. Admin Authentication Bypass — 🔴 TODO

**Issue:** Zero authentication on admin API — anyone can create/delete horses, owners, HLTs

**Risk:** 🔴 CRITICAL — Production security vulnerability

**Plan:**
- Create `api/admin/auth.py` with Firebase Auth middleware
- Protect all `/api/*` endpoints with `@require_auth` decorator
- Update frontend to attach auth headers
- Add `firebase-admin` to dependencies

**ETA:** 3-4 hours

**Status:** 🔴 TODO — See [`docs/sprints/S00_foundation_security.md#phase-4`](docs/sprints/S00_foundation_security.md)

### 8. CORS Wildcard — 🔴 TODO

**Issue:** `Access-Control-Allow-Origin: *` allows any website to make requests

**Risk:** 🟡 HIGH — CSRF-style attacks possible

**Plan:**
- Replace `*` with allowlist from environment variable
- Update `api/ssot/main.py`, `api/assets/main.py`, `api/kyc/main.py`
- Configure allowed origins per environment

**ETA:** 1 hour

**Status:** 🔴 TODO — See [`docs/sprints/S00_foundation_security.md#phase-5`](docs/sprints/S00_foundation_security.md)

---

## Related Documents

- **Plan:** [`GAME_PLAN.md`](GAME_PLAN.md) — 9 checkpoints
- **Current Sprint:** [`docs/sprints/S00_foundation_security.md`](docs/sprints/S00_foundation_security.md) — Sprint Zero plan
- **Current status:** [`docs/PROGRESS.md`](docs/PROGRESS.md) — Live build tracker
- **Overview:** [`docs/BUILD_SUMMARY.md`](docs/BUILD_SUMMARY.md) — High-level summary
- **Laws:** [`AGENTS.md`](AGENTS.md) — Core architecture rules
- **Audit:** [`docs/audit/AUDIT.md`](docs/audit/AUDIT.md) — Quality assessments