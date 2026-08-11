# 01_evolution — Live State

**Last updated:** 2026-07-13 (session protocol: continue.md + STATE.md)
**Canonical for agents:** yes — this file + [`README.md`](README.md) are the only required reads for most sessions.

---

## Agent boot (island protocol)

| Order | File | Role |
|-------|------|------|
| **1** | [`continue.md`](continue.md) | **Next action** — overwrite every session wrap |
| **2** | This file (`STATE.md`) | **Current truth** — architecture, live, remaining work |

**Start:** read continue → this file → do Next action.  
**End:** say *“update the end of session notes”* → overwrite continue + patch this file.  
**Protocol:** [`../docs/SESSION_PROTOCOL.md`](../docs/SESSION_PROTOCOL.md)



## Architecture (canonical)

**Two layers:**

1. **Knowledge repo (live, git SSOT)** — `horses/`, `people/`, `stables/`, `leases/`, `hlts/`, markdown + JSON. Author here at founder speed.
2. **Runtime APIs (retired)** — `api/` Cloud Functions, Firestore, GCS — **billing delinquent, endpoints dead**.

```
Author content → 01_evolution/horses/{slug}/  (git)
Website display → 02_website/src/data/*.json   (synced separately)
Production runtime → GCP (RETIRED — code preserved in api/)
```

---

## What's live

| Component | Status | Notes |
|-----------|--------|-------|
| **Knowledge repo** | ✅ | `python kb-index.py --horse prudentia` — local, no auth |
| **Entity content** | ✅ | Horses, people, stables, leases, HLTs as markdown/JSON |
| **API code (`api/`)** | 🟡 Preserved | SSOT, assets, KYC, email-ingest — not deployed |
| **Local tests** | ✅ | Run via project Justfile / pytest in `api/` |
| **Firebase Auth** | ✅ | Client-side; used by `02_website` |
| **Local assets** | ✅ | 427 files in `_assets/` (pulled from GCS before retirement) |

---

## GCP retired (constraint)

| Component | Status |
|-----------|--------|
| Cloud Functions (`ssot`, `assets`, `kyc`, `email-ingest`) | 🔴 Dead |
| Firestore runtime | 🔴 Not accessible |
| GCS buckets | 🔴 Not accessible — assets local in `_assets/` |

**If billing restored:** `api/` can redeploy; dormant `02_website` GCP paths could reactivate. **Primary path:** post-GCP reframe (local JSON + Stripe on Vercel).

---

## Remaining work

1. **Keep knowledge repo current** — horse profiles, race records, investor update source data
2. **Email-ingest** — local/dev pipeline (`api/email-ingest/`) when env vars available
3. **Mission Control / admin** — **live local** at `_tools/mission-control/` (not under `api/admin` — that path is retired)
4. **Sync path to website** — website still Sheet-first; MC publishes JSON only on explicit Sync confirm

---

## Handoffs (human)

| Item | Action |
|------|--------|
| GCP billing | Restore only if intentional — else treat as retired |
| `STRIPE_SECRET_KEY` on Vercel | Website owns Stripe now — not GCP env |
| GCS pull / Firestore export | Non-critical; scripts ready if billing returns — see `_assets/WHATS_LEFT.md` |
| Firebase Email/Password | Enable in console if signup broken |

---

## Constraints

- **`api/` is the only runtime writer** — when GCP is live; until then, git knowledge repo is SSOT
- **Microchip is durable anchor** — 15-digit ID for every horse
- **Downstream never authors canonical truth** — `02_website`, `04_comms` consume; they don't own horse facts
- **Vertex/Gemini** — retired for inference; see model routing in workspace, not `AGENTS.md` here

---

## Verify (every task)

```bash
cd /home/evo/evo_01/01_evolution
python kb-index.py --stats
# API work (when relevant):
just -f Justfile test-api 2>/dev/null || pytest api/ -q
```

---

## Stale docs (archive reference only)

- `docs/PROGRESS.md` — pre-GCP-retirement sprint tracker (Cloud Functions "live", WIF, etc.)
- `docs/BUILD_SUMMARY.md` — historical overview
- `AGENTS.md` — currently holds model-routing notes, not backend agent rules