# Evolution Stables — Progress

> **STALE for agent boot.** Live state: [`../STATE.md`](../STATE.md). This file is pre-GCP-retirement history.

> **This is the diary.** Session log, what's next, architecture status.
> For what the project is and what exists, see [BUILD_SUMMARY.md](BUILD_SUMMARY.md).

**Current Phase:** 🟢 Phase 1 — MVP Build  
**Last Updated:** 2026-06-24  
**Next Session:** Gmail API credentials, Google STT re-auth, race acceptance parser, Firestore sync

---

## Current State

**Backend (`01_evolution/api/`):** ✅ Live — 3 Cloud Functions deployed with Firebase Auth middleware  
**Admin UI:** ✅ Mission Control running on `:5000` — SPA with horse CRUD, HLT builder, media console  
**Tests:** ✅ 173/173 passing, zero warnings  
**Auth:** ✅ Firebase Auth on 20+ admin endpoints + 3 Cloud Functions  
**CORS:** ✅ Origin-restricted on all Cloud Functions  
**Models:** ✅ Unified in `api/core/models.py` — single source of truth  
**WIF:** ✅ Workload Identity Federation pool + OIDC provider created for Vercel auth  
**Cloud Run:** ✅ `evolution-api-proxy` deployed — IAM bridge for Vercel→CF calls  

**Blockers:** 1 (Vercel OIDC not yet enabled in Vercel dashboard — blocks production auth chain)

---

## Sprint Status

| Sprint | Status | Date |
|--------|--------|------|
| **Sprint Zero** — Foundation & Security | ✅ Complete | 2026-06-10 |
| **Sprint One** — Horse Media Console + Data Sync | 🟡 In Progress | 2026-06-10 |

**Sprint Zero Deliverables:**
- ✅ Unified models (`api/core/models.py`)
- ✅ Test infrastructure — 173/173 passing
- ✅ Admin authentication — Firebase Auth on 20+ endpoints
- ✅ CORS restricted — allowlist, no wildcard
- ✅ Mission Control UI — sign-in/out working
- ✅ Debt sweep — zero backups, zero duplicates, clean pycache
- ✅ Stripe rules documented — `dna/conventions/STRIPE.md`

**Sprint One Deliverables (in progress):**
- [ ] Add 4 Wexford horses: Prudentia, Hottathanafantasy, I-Stole-A-Manolo, First-Gear
- [ ] Fix SSOT API 403 (Cloud Functions auth for email ingest pipeline)
- [ ] Fix SQLite schema mismatch
- [ ] Dedup transcript filenames
- [ ] Push Prudentia transcripts to Firestore
- [ ] Build horse detail media console in Mission Control UI
- [ ] Build `GET /api/horses/{microchip}/media` endpoint

See: [`docs/sprints/S01_horse_media_console.md`](sprints/S01_horse_media_console.md)

---

## Session Log

| Date | Focus | Status |
|------|-------|--------|
| 2026-06-10 | Sprint Zero — Foundation & Security | ✅ Complete |
| 2026-06-11 | Repo hygiene audit — tests, secrets, CORS, docs | ✅ Complete |
| 2026-06-11 | SPA routing fixes — horse navigation, HLT close button | ✅ Complete |
| 2026-06-11 | GCP Auth Blocker — WIF infra, Firebase Auth middleware, Cloud Run proxy | 🟡 In Progress |
| 2026-06-24 | Knowledge Repository Build — 80 files, 10 entity types, verified pedigrees | ✅ Complete |
| 2026-06-24 | Email Ingest Pipeline — model migration, parser fixes, auto-sync | ✅ Complete |

---

## What's Next

1. **Gmail API credentials** — try service account with domain-wide delegation (bypass org policy)
2. **Google STT re-auth** — run `gcloud auth application-default login` in fresh browser
3. **Race acceptance parser** — extract venue + race date from subject line
4. **Investigate transcript #4** — "rib cracker" content mismatch (wrong horse?)
5. 🔴 **Enable Vercel OIDC** in Vercel dashboard (manual step — still blocking production auth chain)
6. Redeploy Vercel, test full auth chain Vercel → Cloud Run → Cloud Function
7. **Push Prudentia transcripts to Firestore** via SSOT API
8. **Build horse detail media console** in Mission Control UI
9. **KYC tests** — Replace placeholder `assert True` tests with real integration tests
10. **CI/CD** — Add `.github/workflows/test.yml` (pytest + lint)

> **Note:** Almanzor x Night Danza is a pending case — held until the horse is named + microchip assigned on loveracing.nz. No action needed until then.

---

## Architecture Status

| System | Status | Details |
|--------|--------|---------|
| **GCP Project** | ✅ Active | `evolution-engine` (851430309148) |
| **Firestore** | ✅ Running | `australia-southeast1`, Standard edition |
| **Cloud Storage** | ✅ 2 buckets | `evolution-horse-images`, `evolution-horse-docs` |
| **Cloud Functions** | ✅ Active (3) | ssot (v13), assets (v5), kyc (v9) — all with Firebase Auth |
| **Cloud Run** | ✅ Active | `evolution-api-proxy` — IAM bridge for Vercel→CF |
| **WIF Pool** | ✅ Created | `vercel-pool` with `vercel-oidc` provider |
| **Service Account** | ✅ Created | `website-api@evolution-engine.iam.gserviceaccount.com` |
| **Firebase** | ✅ Enabled | Web app created, Email/Password + Google auth |
| **Stripe** | ✅ Connected | Sandbox mode, Identity API ready |
| **Admin UI** | ✅ Running | Flask on `:5000`, SQLite-backed |
| **Vercel OIDC** | 🔴 Not enabled | Manual toggle needed in Vercel dashboard |

---

## Related Documents

- **Plan:** [`GAME_PLAN.md`](../GAME_PLAN.md) — 9 checkpoints
- **Overview:** [`BUILD_SUMMARY.md`](BUILD_SUMMARY.md) — High-level summary
- **Live state:** [`STATE.md`](../STATE.md) — canonical (replaces BLOCKERS.md)
- **Laws:** [`AGENTS.md`](../AGENTS.md) — Core architecture rules
- **Audit:** [`audit/AUDIT.md`](audit/AUDIT.md) — Quality assessments
- **Sprints:** [`sprints/`](sprints/) — Sprint plans & completion reports
