# Blockers & Human Handoff Points

**Last Updated:** 2026-06-24

---

## GCP Infrastructure — 🔴 RETIRED (Billing Delinquent)

GCP Cloud Functions, Firestore, and GCS are **retired** — billing is delinquent. Assets have been consolidated locally into `_assets/` (427 files). The website is being reframed to operate without GCP (see `02_website/AGENTS.md` and `02_website/HANDSHAKE.md`).

### What's retired

| Component | Former Status | Current Status |
|---|---|---|
| **GCP Project** (`evolution-engine`, ID: 851430309148) | ✅ RESOLVED | 🔴 RETIRED — billing delinquent |
| **Firestore** (australia-southeast1) | ✅ RESOLVED | 🔴 RETIRED — data not accessible |
| **GCS buckets** (`evolution-horse-images`, `evolution-horse-docs`) | ✅ RESOLVED | 🔴 RETIRED — assets pulled local to `_assets/` |
| **Cloud Functions** (SSOT, Assets, KYC) | ✅ RESOLVED, deployed | 🔴 RETIRED — endpoints dead |
| **GCP ADC credentials** | Configured | 🔴 RETIRED — not used |

### What still works (not GCP-dependent)

| Component | Status | Notes |
|---|---|---|
| **Firebase Auth** | ✅ LIVE | Client-side only, works without GCP backend |
| **Stripe** | ✅ LIVE (pending rewrite) | KYC + Checkout need rewrite to call Stripe directly, not via GCP proxy |
| **Local assets** | ✅ LIVE | 427 files in `_assets/`, symlinks active. See [_assets/WHATS_LEFT.md](../_assets/WHATS_LEFT.md) |

### If GCP billing is restored

The backend code in `api/` is preserved. Cloud Functions can be redeployed. The dormant files in `02_website` (`src/lib/api.ts`, `src/lib/gcp-auth.ts`, `src/app/admin/`) can be reactivated. But the post-GCP reframe is the primary path forward.

---

## Stripe — 🟡 PENDING REWRITE

### Setup (still valid)

- Stripe CLI authenticated for Evolution Stables sandbox (`acct_1TLJdYJNM3QjvBY1`)
- Publishable key: `NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY`
- Secret key: needs to move from GCP env to Vercel env (`STRIPE_SECRET_KEY`)
- Webhook signing secret: needs Stripe Dashboard webhook endpoint for production

### What needs rewriting

| Route | Current (GCP proxy) | Target (direct Stripe) |
|---|---|---|
| `02_website/src/app/api/kyc/create-session/route.ts` | Calls GCP KYC API | Calls `stripe.identity.VerificationSession.create()` directly |
| `02_website/src/app/api/checkout/create-session/route.ts` | Calls GCP Payments API | Calls `stripe.checkout.Session.create()` directly |

**Handoff:** User provides `STRIPE_SECRET_KEY` for Vercel env vars.

---

## Firebase Auth — ✅ LIVE

- Firebase project: `evolution-engine`
- Web app: `1:851430309148:web:41dd7c7e2be68539beced9`
- Config: `NEXT_PUBLIC_FIREBASE_CONFIG` in Vercel env
- Sign-in methods: Email/Password + Google OAuth
- **⚠️ Manual step still needed:** Enable Email/Password at [Firebase Console](https://console.firebase.google.com/project/evolution-engine/authentication → Sign-in method → Enable Email/Password)

---

## Asset Consolidation — ✅ COMPLETE (gaps non-critical)

427 files consolidated into `_assets/`. 2 tasks blocked by GCP billing (non-critical), 2 deferred (code changes), 6 nice-to-have improvements.

See: [_assets/WHATS_LEFT.md](../_assets/WHATS_LEFT.md) for the full status.

### Blocked by GCP (non-critical)

1. **GCS pull** — ~10 CR2 raw files, email ingest videos, auto-generated thumbnails. Script ready (`_assets/gcs_pull.py`). Low impact — CR2 files not needed for web.
2. **Firestore transcript export** — transcripts only accessible via API. Would give local JSON copies. Script needed once billing restored.

**If billing stays blocked:** Both are non-critical. The system works without them.

---

## Sprint Zero Items — Historical (completed before GCP retirement)

### ~~Model Fragmentation~~ ✅ RESOLVED
- Created `api/core/models.py` as single source of truth
- Deleted conflicting model directories
- See: [`docs/sprints/S00_foundation_security.md`](docs/sprints/S00_foundation_security.md)

### ~~Broken Test Infrastructure~~ ✅ RESOLVED
- Added Flask, pytest, pytest-flask to requirements
- Fixed all model imports

### ~~Admin Authentication Bypass~~ 🔴 MOVED TO DORMANT
- Was: zero auth on admin API — critical production vulnerability
- Now: admin API is dormant (GCP retired). No live endpoints = no live vulnerability.
- If GCP returns: this becomes a critical blocker again.

### ~~CORS Wildcard~~ 🔴 MOVED TO DORMANT
- Was: `Access-Control-Allow-Origin: *` on all Cloud Functions
- Now: Cloud Functions are dead. No CORS to exploit.
- If GCP returns: this needs fixing before redeployment.

---

## New Blockers (Post-GCP Reframe)

### 1. Spreadsheet Inventory Design — 🔴 TODO
- Define Google Sheets structure for horses, HLTs, trainers, owners, holdings
- Create sheets (user to create, or agent to design)
- Map SSOT schema fields to spreadsheet columns

### 2. Sync Script — 🔴 TODO
- Write `scripts/sync_inventory.py` — reads Google Sheets, writes `src/data/*.json`
- Handles the "replay" workflow: edit sheet → run script → rebuild site

### 3. Stripe Route Rewrite — 🔴 TODO
- Rewrite `api/kyc/create-session/route.ts` — direct Stripe, no GCP
- Rewrite `api/checkout/create-session/route.ts` — direct Stripe, no GCP
- Needs `STRIPE_SECRET_KEY` in Vercel env

### 4. Marketplace/MyStable Rewire — 🔴 TODO
- `marketplace/page.tsx` — read from `src/data/hlts.json` instead of `getHlts()` API call
- `mystable/page.tsx` — read from `src/data/holdings.json` instead of `getHoldings()` API call

---

## Related Documents

- **Plan:** [`GAME_PLAN.md`](GAME_PLAN.md) — Post-GCP reframe
- **Website:** [`../02_website/AGENTS.md`](../02_website/AGENTS.md) — Website agent rules (post-GCP)
- **Website handshake:** [`../02_website/HANDSHAKE.md`](../02_website/HANDSHAKE.md) — Data + auth contract (post-GCP)
- **Asset status:** [`../_assets/WHATS_LEFT.md`](../_assets/WHATS_LEFT.md) — Asset consolidation
- **Laws:** [`AGENTS.md`](AGENTS.md) — Core architecture rules