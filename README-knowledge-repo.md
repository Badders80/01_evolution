# Knowledge Repository

**Purpose:** Local, no-auth, instantly accessible knowledge base for Evolution Stables. Author content here at founder speed. Push to Firestore via the API when ready for production.

---

## Structure

```
01_evolution/
├── horses/              Per-horse content (profiles, listings, pedigree, race records)
│   └── {slug}/
│       ├── tokinvest-listing.md   Verbatim archive (frozen)
│       ├── profile.md             Living profile (Evolution voice)
│       ├── pedigree.json           Structured pedigree data (verified from loveracing.nz)
│       └── race-record.json        Structured race starts & results (verified from loveracing.nz)
├── people/             One file per person, tagged by role
│   └── {slug}/profile.md          Roles: trainer, owner, breeder, jockey
├── stables/            Stables as entities (facilities, location, history)
│   └── {slug}/profile.md
├── pedigrees/          Sire/dam knowledge — why a bloodline matters
│   └── {slug}/profile.md
├── press/              Archived articles, race reports
│   └── {slug}.md                  Tagged to horses, people, stables, tracks
├── governing-bodies/   Regulatory bodies (NZTR, Dubai Racing Club)
│   └── {slug}/profile.md
├── leases/             Commercial lease terms per horse (JSON)
│   └── lse-XXX.json               Token pricing, investor splits, % leased
├── hlts/               HLT campaign records (horse + owner + trainer + lease)
│   └── {slug}.md                  Links all entities for a syndication campaign
├── kb-index.py         Query script — search by tag, type, role, entity
└── README-knowledge-repo.md   You are here
```

## How It Works

**Folders are for physical organization. Tags are for retrieval.**

Every markdown file has YAML frontmatter with tags and cross-entity links. A file lives in one folder (no duplication) but is findable through any of its tags.

### Example: "Write me a bit on First Gear"

```bash
python kb-index.py --horse first-gear
```

Returns:
- `horses/first-gear/profile.md` — the horse profile
- `press/first-gear-hawkes-bay-six-figure-offer.md` — the NZ Herald article
- `people/stephen-gray/profile.md` — trainer & owner
- `stables/stephen-gray-racing/profile.md` — the stable (SGR)
- `pedigrees/derryn/profile.md` — the sire

All linked through frontmatter tags. No duplication. No database. No auth.

## Query Examples

```bash
# List everything
python kb-index.py --list

# Show stats
python kb-index.py --stats

# Find all press about a horse
python kb-index.py --horse first-gear --type press

# Find all trainers
python kb-index.py --role trainer

# Find all owners
python kb-index.py --role owner

# Find everyone linked to Wexford Stables
python kb-index.py --stable wexford-stables

# Find all horses
python kb-index.py --type horse

# Find by tag
python kb-index.py --tag racing

# Find all files linked to an owner
python kb-index.py --owner bax-bloodstock

# Find lease terms for a horse
python kb-index.py --lease lse-002

# Find HLT campaign for a horse
python kb-index.py --hlt prudentia
```

## Frontmatter Schema

Every `.md` file has YAML frontmatter. Common fields:

| Field | Type | Description |
|-------|------|-------------|
| `slug` | string | Unique identifier (kebab-case) |
| `type` | string | `horse`, `person`, `entity`, `stable`, `pedigree`, `press`, `governing-body`, `hlt` |
| `tags` | list | Free-form tags for retrieval |
| `roles` | list | For people: `trainer`, `owner`, `breeder`, `jockey` |
| `horses` | list | Slugs of linked horses |
| `people` | list | Slugs of linked people |
| `stables` | list | Slugs of linked stables |
| `pedigrees` | list | Slugs of linked pedigrees |
| `trainer` | string | Trainer slug (for horses) |
| `sire` | string | Sire slug (for horses/pedigrees) |
| `dam` | string | Dam slug (for horses) |
| `owner` | string | Owner slug (for horses/HLTs) |
| `breeder` | string | Breeder slug (for horses) |
| `lease` | string | Lease ID (for HLTs) |
| `governing_body` | string | Governing body slug (for HLTs) |
| `microchip` | string | 15-digit microchip (for horses) |
| `backend_id` | string | Backend Firestore ID (OWN-001, TRN-001, etc.) |

## Relationship to Backend

| | Knowledge Repository | Backend (API/Firestore) |
|---|---|---|
| **Now** | Daily working surface | Exists, tested, dormant |
| **Go-live** | Authoring source of truth | Receives pushed data via API |
| **Post-launch** | Author updates here → push | Serves investors at runtime |

The repository feeds the backend. The backend doesn't feed the repository.

## Relationship to Assets

Images and videos live in `_assets/horses/{slug}/images/` — local, not in git (see top-level `.gitignore`). The repository references them by path in frontmatter. The website uses copies in `02_website/public/images/`.

## Adding New Content

### New horse
1. Create `horses/{slug}/profile.md` with frontmatter tags
2. Add `tokinvest-listing.md` if sourced from tokinvest
3. Add `pedigree.json` and `race-record.json` for structured data
4. Download images to `_assets/horses/{slug}/images/`

### New person
1. Create `people/{slug}/profile.md` with `roles` tag
2. Link to horses via `horses:` field

### New press article
1. Create `press/{slug}.md` with `source_url`, `horses`, `people`, `stables` tags
2. Archive the article content (or key facts if paywalled)

### New governing body
1. Create `governing-bodies/{slug}/profile.md` with `code` and `status` fields
2. Link to horses via `horses:` field

### New lease
1. Create `leases/lse-XXX.json` with full commercial terms (NZD + AED where applicable)
2. Include `backend_id` (LSE-XXX) for Firestore mapping

### New HLT campaign
1. Create `hlts/{slug}.md` linking horse + owner + trainer + lease + governing body
2. Include `owner_id`, `trainer_id`, `governing_body_code` backend IDs in frontmatter

### Ingest a URL
Say "ingest this URL" and the system will:
1. Fetch the article
2. Extract entities (horses, people, stables, tracks)
3. Create a press file with cross-linked frontmatter tags