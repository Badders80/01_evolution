# Evolution Stables — Progress

> **This is the diary.** Session log, what's next, architecture status.
> For what the project is and what exists, see [BUILD_SUMMARY.md](BUILD_SUMMARY.md).

**Current Phase:** 🟢 Phase 1 — MVP Build  
**Last Updated:** 2026-06-11  
**Next Session:** Sprint One — Horse Media Console + Data Sync

---

## Current State

**Backend (`01_evolution/api/`):** ✅ Live — 3 Cloud Functions deployed (ssot, assets, kyc)  
**Admin UI:** ✅ Mission Control running on `:5000` — SPA with horse CRUD, HLT builder, media console  
**Tests:** ✅ 173/173 passing, zero warnings  
**Auth:** ✅ Firebase Auth on 20+ admin endpoints  
**CORS:** ✅ Origin-restricted on all Cloud Functions  
**Models:** ✅ Unified in `api/core/models.py` — single source of truth  

**Blockers:** 0 (all resolved)

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

---

## What's Next

1. **Sprint One** — Horse Media Console + Data Sync (see sprint doc)
2. **KYC tests** — Replace placeholder `assert True` tests with real integration tests
3. **Payments tests** — Add test coverage (currently zero)
4. **CI/CD** — Add `.github/workflows/test.yml` (pytest + lint)
5. **Linting** — Add `pyproject.toml` with ruff config
6. **`backfill_5_days.py`** — ✅ Deleted (consolidated into `backfill.py`)

---

## Architecture Status

| System | Status | Details |
|--------|--------|---------|
| **GCP Project** | ✅ Active | `evolution-engine` (851430309148) |
| **Firestore** | ✅ Running | `australia-southeast1`, Standard edition |
| **Cloud Storage** | ✅ 2 buckets | `evolution-horse-images`, `evolution-horse-docs` |
| **Cloud Functions** | ✅ 3 deployed | `ssot`, `assets` (with bulk-upload), `kyc` |
| **Firebase** | ✅ Enabled | Web app created, Email/Password + Google auth |
| **Stripe** | ✅ Connected | Sandbox mode, Identity API ready |
| **Admin UI** | ✅ Running | Flask on `:5000`, SQLite-backed |

---

## Related Documents

- **Plan:** [`GAME_PLAN.md`](../GAME_PLAN.md) — 9 checkpoints
- **Overview:** [`BUILD_SUMMARY.md`](BUILD_SUMMARY.md) — High-level summary
- **Blockers:** [`BLOCKERS.md`](../BLOCKERS.md) — Resolved issues
- **Laws:** [`AGENTS.md`](../AGENTS.md) — Core architecture rules
- **Audit:** [`audit/AUDIT.md`](audit/AUDIT.md) — Quality assessments
- **Sprints:** [`sprints/`](sprints/) — Sprint plans & completion reports
