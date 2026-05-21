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

## Related Documents

- **Plan:** [`GAME_PLAN.md`](GAME_PLAN.md) — 9 checkpoints
- **Current status:** [`docs/PROGRESS.md`](docs/PROGRESS.md) — Live build tracker
- **Overview:** [`docs/BUILD_SUMMARY.md`](docs/BUILD_SUMMARY.md) — High-level summary
- **Laws:** [`AGENTS.md`](AGENTS.md) — Core architecture rules
- **Audit:** [`docs/audit/AUDIT.md`](docs/audit/AUDIT.md) — Quality assessments