# Evolution — Minimum Viable Business Surface

Single workspace for the Evolution Stables platform.

## Structure

```
evolution/
├── api/          Cloud Functions (the only data writers)
│   ├── models/   Shared Pydantic schemas
│   ├── ssot/     Horse, Owner, Trainer, HLT, Doc generation
│   ├── assets/   Image upload, retrieve, delete
│   └── kyc/      Stripe Identity verification
├── dna/          Shared design system + schemas
└── docs/         Migration + strategy documents
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

## Related Documents

- **Frontend:** [`02_website/`](../02_website/) — Investor/user-facing website
- **Plan:** [`GAME_PLAN.md`](GAME_PLAN.md) — Backend roadmap (Checkpoints 1-9)
- **Current status:** [`docs/PROGRESS.md`](docs/PROGRESS.md) — Live build tracker
- **Overview:** [`docs/BUILD_SUMMARY.md`](docs/BUILD_SUMMARY.md) — High-level summary
- **Blockers:** [`BLOCKERS.md`](BLOCKERS.md) — Resolved issues
- **Laws:** [`AGENTS.md`](AGENTS.md) — Core architecture rules
- **Audit:** [`docs/audit/AUDIT.md`](docs/audit/AUDIT.md) — Quality assessments