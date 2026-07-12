# Evolution — Minimum Viable Business Surface

Single workspace for the Evolution Stables platform.


## Agent / session boot

**This folder is an island.** Do not invent “what’s next” from chat.

| Order | File |
|-------|------|
| **1** | [`continue.md`](continue.md) |
| **2** | [`STATE.md`](STATE.md) |

```text
Read continue.md and STATE.md. What's next?
```

End session: *“update the end of session notes”* → overwrite continue + patch STATE.  
Full protocol: [`../docs/SESSION_PROTOCOL.md`](../docs/SESSION_PROTOCOL.md)

---

## Structure

```
evolution/
├── api/          Cloud Functions (the only data writers)
│   ├── models/   Shared Pydantic schemas
│   ├── ssot/     Horse, Owner, Trainer, HLT, Doc generation
│   ├── assets/   Image upload, retrieve, delete
│   └── kyc/      Stripe Identity verification
├── dna/          Shared design system + schemas
├── docs/         Migration + strategy documents
├── horses/       Knowledge repo — per-horse content (profiles, listings, pedigree, race records)
├── people/       Knowledge repo — trainers, owners, breeders (tagged by role)
├── stables/      Knowledge repo — stable entities (Wexford, SGR, Logan Racing)
├── pedigrees/    Knowledge repo — sire/dam knowledge (verified from loveracing.nz + breednet)
├── press/        Knowledge repo — archived articles, race reports
├── governing-bodies/  Knowledge repo — NZTR, Dubai Racing Club
├── leases/       Knowledge repo — commercial lease terms (JSON)
├── hlts/         Knowledge repo — HLT campaign records
├── kb-index.py   Query script for the knowledge repo
└── README-knowledge-repo.md  Documentation for the knowledge repo
```

## Knowledge Repository

The knowledge repository is a local, no-auth knowledge base that mirrors the backend's entity model.
Author content here at founder speed. Push to Firestore via the API when ready for production.

See [`README-knowledge-repo.md`](README-knowledge-repo.md) for full documentation.

```bash
# Query the knowledge repo
python kb-index.py --horse prudentia
python kb-index.py --role owner
python kb-index.py --stats
```

## Quick Start

```bash
# Install API dependencies
cd api && pip install -r requirements.txt

# Run API locally (requires gcloud auth + Firestore emulator)
cd api/ssot && functions-framework --target=ssot --port=8080
cd api/assets && functions-framework --target=assets --port=8081
cd api/kyc && functions-framework --target=kyc --port=8082

# Frontend is in 02_website/ (separate workspace)
```

## Architecture Rules

1. **`api/` is the only data writer.** The app never writes to Firestore directly.
2. **Microchip is the durable anchor.** Every horse is identified by its 15-digit microchip.
3. **HLT status is a state machine.** `draft → reviewed → publish_ready → published`
4. **Assets are organized by entity.** `horse/{microchip}/` in GCS.
5. **DNA schemas are the contract.** Pydantic models and React forms both validate against the same JSON Schemas.

## Data Source

Every NZ thoroughbred has a loveracing.nz Stud Book page:
- URL pattern: `https://loveracing.nz/Breeding/{HorseID}/{NameSlug}.aspx`
- Example: `https://loveracing.nz/Breeding/427416/Prudentia-NZ-2021.aspx`
- Key fields: Microchip, Life Number, Name, Foaling Date, Sex, Colour, Sire, Dam, Breeder, Brands

## Environment Variables

| Key | Purpose | Required |
|-----|---------|----------|
| `GCP_PROJECT` | Google Cloud project ID | Yes |
| `GOOGLE_APPLICATION_CREDENTIALS` | GCP service account key | Yes (production) |
| `STRIPE_SECRET_KEY` | Stripe server-side key | Yes (for KYC) |
| `STRIPE_WEBHOOK_SECRET` | Stripe webhook verification | Yes (for KYC) |
| `STRIPE_PUBLISHABLE_KEY` | Stripe client-side key | Yes (for KYC) |
| `FIREBASE_CONFIG` | Firebase project config JSON | Yes (for auth) |

---

## Agent boot

[`STATE.md`](STATE.md) → this file. Add [`../SURFACES.md`](../SURFACES.md) §3 when deploying APIs.

## Related Documents

- **Frontend:** [`02_website/`](../02_website/) — Investor/user-facing website
- **Live state:** [`STATE.md`](STATE.md) — architecture truth, handoffs, verify
- **Plan (sprint):** [`GAME_PLAN.md`](GAME_PLAN.md) — Backend roadmap
- **History:** [`docs/PROGRESS.md`](docs/PROGRESS.md) — pre-GCP-retirement tracker (stale for boot)
- **Audit:** [`docs/audit/AUDIT.md`](docs/audit/AUDIT.md) — Quality assessments