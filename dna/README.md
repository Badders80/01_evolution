# DNA — Design System

**Purpose:** Shared design system, schemas, and conventions for Evolution Stables.

**DNA** = Design, Naming, Architecture — the foundational patterns that keep the codebase consistent.

---

## Structure

```
dna/
├── schemas/               ← JSON Schemas for all entities
│   ├── horse.json         ← Horse record (microchip anchor)
│   ├── owner.json         ← Owner (individual/syndicate/corporate)
│   ├── trainer.json       ← Trainer (NZTR-licensed)
│   ├── hlt.json           ← HLT (with status lifecycle)
│   └── asset.json         ← Asset (extensible entity types)
├── brand/                 ← Brand guidelines
│   ├── BRAND_SYSTEM.md    ← Colors, typography, spacing
│   └── VOICE_SYSTEM.md    ← Tone, terminology, writing rules
├── conventions/           ← Development conventions
│   └── CONVENTIONS.md     ← Naming, API patterns, security
└── outcomes/              ← Why decisions were made
    └── WHY.md             ← Architecture rationale
```

---

## JSON Schemas

All schemas validate data at:
- **API layer** — Pydantic models mirror these exactly
- **Frontend** — React forms validate against these
- **Database** — Firestore documents follow these structures

| Schema | Primary Key | Key Fields |
|--------|-------------|------------|
| **horse.json** | `microchip` (15 digits) | life_number, loveracing_id, name, foaling_date, sex, colour, sire, dam, breeder |
| **owner.json** | `id` (auto) | type (individual/syndicate/corporate), name, email, phone, kyc_status |
| **trainer.json** | `id` (auto) | name, nztr_license, phone, email, address |
| **hlt.json** | `id` (auto) | horse_id, owner_id, trainer_id, status (draft→reviewed→publish_ready→published), documents |
| **asset.json** | `id` (auto) | entity_type, entity_id, file_path, mime_type, size, uploaded_at |

---

## Brand System

- **Primary Color:** Gold `#d4a964`
- **Secondary Color:** Black `#121212`
- **Typography:** System fonts (Inter, system-ui)
- **Spacing:** 4px grid (Tailwind spacing scale)
- **Voice:** Professional, concise, investor-focused

See [`dna/brand/`](dna/brand/) for full guidelines.

---

## Conventions

- **Naming:** kebab-case files, PascalCase components, snake_case DB fields
- **API:** RESTful patterns, Pydantic validation
- **Security:** Environment variables for secrets, no hardcoded credentials
- **Testing:** pytest for API, Jest for frontend

See [`dna/conventions/`](dna/conventions/) for full conventions.

---

## Related

- **[AGENTS.md](../AGENTS.md)** — Core architecture laws (DNA enforces these)
- **[api/models/](../api/models/)** — Pydantic models (mirror JSON Schemas)
- **[app/src/lib/](../app/src/lib/)** — Frontend utilities (use DNA conventions)
