# API Layer

**Purpose:** Cloud Functions that serve as the single source of truth (SSOT) for Evolution Stables data.

**Core Principle:** `api/` is the only data writer. The app never writes to Firestore directly.

---

## Structure

```
api/
├── models/              ← Shared Pydantic schemas (Horse, Owner, Trainer, HLT, Asset)
├── ssot/                ← SSOT API (horses, owners, trainers, HLTs, docs)
├── assets/              ← Assets API (upload, retrieve, delete)
├── kyc/                 ← KYC API (Stripe Identity)
├── requirements.txt     ← Python dependencies
└── .env.api.yaml        ← Environment config (Stripe keys, GCP project, buckets)
```

---

## Deployed Functions

| Function | URL | Routes | Status |
|----------|-----|--------|--------|
| **ssot** | `https://australia-southeast1-evolution-engine.cloudfunctions.net/ssot` | `/horses`, `/owners`, `/trainers`, `/hlts`, `/docs` | ✅ Deployed |
| **assets** | `https://australia-southeast1-evolution-engine.cloudfunctions.net/assets` | `/upload`, `/retrieve`, `/delete` | ✅ Deployed |
| **kyc** | `https://australia-southeast1-evolution-engine.cloudfunctions.net/kyc` | `/create-session`, `/webhook` | ✅ Deployed |

---

## Architecture Laws

1. **Microchip is the anchor** — Every horse identified by 15-digit microchip
2. **Pydantic validation** — All request/response data validated against schemas
3. **Environment variables** — Secrets in `.env.api.yaml`, never in code
4. **1st gen Cloud Functions** — Deployed as 1st gen for compatibility

---

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Run locally (SSOT)
cd api/ssot && functions-framework --target=ssot --port=8080

# Run locally (Assets)
cd api/assets && functions-framework --target=assets --port=8081

# Run locally (KYC)
cd api/kyc && functions-framework --target=kyc --port=8082
```

---

## Related

- **[AGENTS.md](../AGENTS.md)** — Core architecture laws
- **[docs/PROGRESS.md](../docs/PROGRESS.md)** — Current build status
- **[dna/schemas/](../dna/schemas/)** — JSON Schemas (Pydantic mirrors these)
