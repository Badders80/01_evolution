# Evolution — API Development Skill

**Purpose:** Create, update, and test Cloud Functions API endpoints for Evolution Stables.

**When to use:**
- Adding new API endpoints to `api/ssot/`, `api/assets/`, or `api/kyc/`
- Modifying existing Pydantic models
- Writing API tests
- Debugging API responses

---

## Workflow

### 1. Add/Update Pydantic Model (if needed)

**Location:** `api/models/__init__.py`

**Rules:**
- Must match JSON Schema in `dna/schemas/` exactly
- Use `snake_case` for field names
- Include `created_at` and `updated_at` timestamps
- Primary key: `microchip` for horses, auto-ID for others

**Example:**
```python
class HorseCreate(BaseModel):
    microchip: str  # 15 digits, required
    name: str
    foaling_date: date
    sex: str
    colour: str
    sire_name: str
    dam_name: str
    breeder_name: str
    life_number: Optional[str] = None
    brands: Optional[str] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
```

### 2. Create API Route

**Location:** `api/ssot/routes/{entity}.py` (or `assets/`, `kyc/`)

**Pattern:**
```python
from fastapi import APIRouter, Request
from models import HorseCreate, Horse
from google.cloud import firestore

router = APIRouter()
db = firestore.Client()

@router.post("/horses")
async def create_horse(request: Request) -> Horse:
    data = await request.json()
    horse = HorseCreate(**data)
    
    # Validate microchip
    if len(horse.microchip) != 15 or not horse.microchip.isdigit():
        raise HTTPException(status_code=400, detail="Microchip must be exactly 15 digits")
    
    # Check for duplicates
    doc_ref = db.collection("horses").document(horse.microchip)
    if doc_ref.get().exists:
        raise HTTPException(status_code=409, detail="Horse with this microchip already exists")
    
    # Create
    doc_ref.set(horse.model_dump())
    return Horse(**doc_ref.get().to_dict())
```

**Endpoints to implement:**
- `POST /{entity}` — Create (201)
- `GET /{entity}/{id}` — Read one (200)
- `GET /{entity}` — Read list (200)
- `PATCH /{entity}/{id}` — Update (200)
- `DELETE /{entity}/{id}` — Delete (200)

### 3. Register Route

**Location:** `api/ssot/routes/__init__.py` (or `assets/`, `kyc/`)

```python
from .horses import router as horses_router
from .owners import router as owners_router

__all__ = ["horses_router", "owners_router"]
```

### 4. Write Tests

**Location:** `api/ssot/tests/test_{entity}.py`

**Pattern:**
```python
import pytest
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

def test_create_horse():
    response = client.post("/horses", json={
        "microchip": "985125000126462",
        "name": "Prudentia NZ",
        "foaling_date": "2021-08-15",
        "sex": "Mare",
        "colour": "Bay",
        "sire_name": "Sacred Falls",
        "dam_name": "Prudent",
        "breeder_name": "Test Breeder"
    })
    assert response.status_code == 201
    data = response.json()
    assert data["microchip"] == "985125000126462"

def test_duplicate_microchip():
    # ... create first horse ...
    # ... try to create again ...
    assert response.status_code == 409
```

### 5. Test Locally

```bash
# Run API
just run-ssot

# In another terminal, test endpoints
curl -X POST http://localhost:8080/horses \
  -H "Content-Type: application/json" \
  -d '{"microchip": "985125000126462", ...}'

# Run tests
just test-ssot
```

### 6. Deploy

```bash
gcloud functions deploy ssot \
  --runtime python311 \
  --trigger-http \
  --allow-unauthenticated \
  --entry-point ssot \
  --region australia-southeast1
```

---

## Validation Rules

### Microchip
- Exactly 15 digits
- Numeric only
- Natural key from loveracing.nz
- Never changes

### HLT Status
- State machine: `draft → reviewed → publish_ready → published`
- Step 1 only: `draft` and `reviewed`
- Validate transitions in PATCH handler

### Assets
- Organized by entity: `horse/{microchip}/`, `owner/{id}/`
- Store metadata in Firestore: `entity_type`, `entity_id`, `gcs_path`
- GCS path format: `{entity_type}/{entity_id}/{uuid}.{ext}`

---

## Common Pitfalls

❌ **Never write to Firestore from the app** — All writes through Cloud Functions only  
❌ **Never use horse name as primary key** — Names change, microchips don't  
❌ **Never skip validation** — Pydantic models must match JSON Schema  
❌ **Never hardcode GCS paths** — Use entity-based organization  
❌ **Never create bi-directional sync** — Downstream systems are clients only  

---

## Related Files

- **Models:** `api/models/__init__.py`
- **Routes:** `api/ssot/routes/`, `api/assets/routes/`, `api/kyc/routes/`
- **Tests:** `api/ssot/tests/`, `api/assets/tests/`, `api/kyc/tests/`
- **Schemas:** `dna/schemas/*.json`
- **Conventions:** `dna/conventions/CONVENTIONS.md`
- **Why:** `dna/outcomes/WHY.md`

---

## Examples

### Create Horse Endpoint
See: `api/ssot/routes/horses.py`

### Upload Asset Endpoint
See: `api/assets/routes/upload.py`

### Create KYC Session
See: `api/kyc/routes/create_session.py`
