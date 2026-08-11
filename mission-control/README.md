# Mission Control

**Canonical** local operator control plane for Evolution Stables.

```bash
cd ~/evo_01/_tools/mission-control
python3 admin_server.py
# → http://127.0.0.1:5000
```

Island docs (boot): [`../continue.md`](../continue.md) · [`../STATE.md`](../STATE.md) · [`../PLAN.md`](../PLAN.md)

---

## What it is

- Horses, bloodstock owners, trainers, leases, **HLT** listings, documents  
- Marketplace content (story / next_up / media)  
- Draft **term sheet** + **investor pack** (PDS+SA) generation  
- **Sync:** preview → confirm → `02_website/src/data/*.json`

**HLT** = listing/agreement entity (kept as a domain term). Product name is **Mission Control**.

---

## Not here

| Path | Status |
|------|--------|
| `_tools/hlt-mission-control/` | Renamed → this folder |
| `_tools/investor-pack-wizard/` | **Removed** — `admin/generators/pack_lib.py` |
| `01_evolution/api/admin*` | Retired stubs |

---

## Key behaviours

- Horse tabs: Identity · Marketplace · Media · Links  
- HLT Detail: term sheet freeze + PDS/SA draft pack  
- Sync page: confirm-only website JSON (no silent dual-write)  
- Google Sheet push: not implemented  
- Legal lock → `02_website/public/documents/{slug}/`: not automated yet  

---

## Document & media paths

| Role | Path |
|------|------|
| Authoring SSOT | `_assets/horses/{slug}/` (images, documents, term_sheets) |
| Investor-facing PDFs | `02_website/public/documents/{slug}/` |
| MC upload scratch | `admin/uploads/` (not SSOT) |
| Local DB | `admin/ssot_local.db` |

---

## Layout

```
mission-control/
├── admin_server.py
├── sync_service.py
├── admin/
│   ├── db.py
│   ├── generators/     # term_sheet, investor_pack, pack_lib
│   ├── ssot_local.db
│   └── uploads/
└── static/             # SPA
```
