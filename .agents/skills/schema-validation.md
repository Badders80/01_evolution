# Evolution — Schema & Validation Skill

**Purpose:** Manage JSON Schemas and ensure consistency between frontend forms and backend Pydantic models.

**When to use:**
- Adding new fields to entities
- Creating validation schemas
- Debugging validation errors
- Ensuring frontend/backend consistency

---

## Core Principle

**DNA schemas are the contract** — Both Pydantic models (`api/models/`) and React forms (`app/src/`) must validate against the same JSON Schemas in `dna/schemas/`.

---

## Workflow

### 1. Update JSON Schema

**Location:** `dna/schemas/{entity}.json`

**Example: Adding a field to horse.json**
```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "type": "object",
  "title": "Horse",
  "required": ["microchip", "name", "foaling_date", "sex", "colour", "sire_name", "dam_name", "breeder_name"],
  "properties": {
    "microchip": {
      "type": "string",
      "pattern": "^[0-9]{15}$",
      "description": "15-digit microchip from loveracing.nz"
    },
    "name": {
      "type": "string",
      "minLength": 1,
      "maxLength": 100
    },
    "foaling_date": {
      "type": "string",
      "format": "date"
    },
    "sex": {
      "type": "string",
      "enum": ["Colt", "Filly", "Stallion", "Mare", "Gelding"]
    },
    "colour": {
      "type": "string",
      "enum": ["Bay", "Brown", "Chestnut", "Grey", "Black", "White", "Roan", "Palomino"]
    },
    "sire_name": {
      "type": "string",
      "minLength": 1
    },
    "dam_name": {
      "type": "string",
      "minLength": 1
    },
    "breeder_name": {
      "type": "string",
      "minLength": 1
    },
    "life_number": {
      "type": "string",
      "nullable": true
    },
    "brands": {
      "type": "string",
      "nullable": true
    },
    "created_at": {
      "type": "string",
      "format": "date-time"
    },
    "updated_at": {
      "type": "string",
      "format": "date-time"
    }
  }
}
```

### 2. Update Pydantic Model

**Location:** `api/models/__init__.py`

```python
from pydantic import BaseModel, Field, field_validator
from datetime import date, datetime
from typing import Optional

class HorseCreate(BaseModel):
    microchip: str
    name: str = Field(..., min_length=1, max_length=100)
    foaling_date: date
    sex: str  # Validate against enum in schema
    colour: str  # Validate against enum in schema
    sire_name: str
    dam_name: str
    breeder_name: str
    life_number: Optional[str] = None
    brands: Optional[str] = None
    
    @field_validator('microchip')
    @classmethod
    def validate_microchip(cls, v):
        if len(v) != 15 or not v.isdigit():
            raise ValueError('Microchip must be exactly 15 digits')
        return v
    
    class Config:
        json_schema_extra = {
            "$schema": "http://json-schema.org/draft-07/schema#",
            "title": "Horse",
        }
```

### 3. Update React Form

**Location:** `app/src/app/admin/horses/new/page.tsx`

```tsx
import { horseSchema } from '@/lib/schemas'

// Form validation
function validateHorseData(data: any) {
  const result = horseSchema.safeParse(data)
  if (!result.success) {
    return result.error.errors.map(err => ({
      field: err.path.join('.'),
      message: err.message,
    }))
  }
  return []
}

// Form field with validation
<input
  name="microchip"
  type="text"
  pattern="[0-9]{15}"
  minLength={15}
  maxLength={15}
  required
  className="w-full border rounded px-3 py-2"
/>
```

### 4. Share Schema with Frontend

**Option A: Import JSON directly**
```ts
// app/src/lib/schemas.ts
import horseSchema from '../../../dna/schemas/horse.json'

export { horseSchema }
```

**Option B: Generate TypeScript types**
```bash
# Install json-schema-to-typescript
npm install -D json-schema-to-typescript

# Generate types
cd dna/schemas
npx json2ts --input horse.json --output ../../app/src/types/horse.ts
```

**Generated TypeScript:**
```ts
export interface Horse {
  microchip: string
  name: string
  foaling_date: string
  sex: string
  colour: string
  sire_name: string
  dam_name: string
  breeder_name: string
  life_number?: string | null
  brands?: string | null
  created_at: string
  updated_at: string
}
```

---

## Validation Patterns

### Backend (Pydantic)

```python
from pydantic import BaseModel, field_validator, ValidationError

class HorseCreate(BaseModel):
    microchip: str
    name: str
    
    @field_validator('microchip')
    @classmethod
    def validate_microchip(cls, v):
        if len(v) != 15:
            raise ValueError('Microchip must be 15 digits')
        if not v.isdigit():
            raise ValueError('Microchip must be numeric')
        return v

# Usage
try:
    horse = HorseCreate(**request_data)
except ValidationError as e:
    return {"error": str(e)}, 400
```

### Frontend (Zod or manual)

```tsx
// Manual validation matching JSON Schema
function validateMicrochip(value: string): string | null {
  if (value.length !== 15) {
    return 'Microchip must be exactly 15 digits'
  }
  if (!/^\d{15}$/.test(value)) {
    return 'Microchip must be numeric only'
  }
  return null
}

// Form validation
const errors = validateMicrochip(formData.microchip)
if (errors) {
  setError(errors)
  return
}
```

---

## Schema Files

| File | Entity | Primary Key | Status Field |
|------|--------|-------------|--------------|
| `horse.json` | Horse | `microchip` (15 digits) | — |
| `owner.json` | Owner | `id` (auto) | — |
| `trainer.json` | Trainer | `id` (auto) | — |
| `hlt.json` | HLT | `id` (auto) | `status` (draft → reviewed → publish_ready → published) |
| `asset.json` | Asset | `id` (auto) | — |

---

## Common Validation Rules

### Microchip
- **Pattern:** `^[0-9]{15}$`
- **Required:** Yes
- **Immutable:** Yes
- **Source:** loveracing.nz

### Dates
- **Format:** ISO 8601 (`YYYY-MM-DD`)
- **Validation:** Must be valid date, not in future (for foaling_date)

### Enums
- **Sex:** `Colt`, `Filly`, `Stallion`, `Mare`, `Gelding`
- **Colour:** `Bay`, `Brown`, `Chestnut`, `Grey`, `Black`, `White`, `Roan`, `Palomino`
- **HLT Status:** `draft`, `reviewed`, `publish_ready`, `published`

### Optional Fields
- `life_number`: Nullable string
- `brands`: Nullable string
- All fields marked `"nullable": true` in schema

---

## Testing Validation

### Backend Tests

```python
def test_invalid_microchip():
    response = client.post("/horses", json={
        "microchip": "123",  # Too short
        "name": "Test Horse"
    })
    assert response.status_code == 400
    assert "microchip" in response.json()["error"]

def test_valid_microchip():
    response = client.post("/horses", json={
        "microchip": "985125000126462",
        "name": "Test Horse",
        # ... all required fields ...
    })
    assert response.status_code == 201
```

### Frontend Tests

```tsx
import { render, screen, fireEvent } from '@testing-library/react'
import HorseCreateForm from './new/page'

test('shows microchip validation error', async () => {
  render(<HorseCreateForm />)
  
  const microchipInput = screen.getByLabelText(/microchip/i)
  fireEvent.change(microchipInput, { target: { value: '123' } })
  fireEvent.click(screen.getByText(/create/i))
  
  expect(await screen.findByText(/15 digits/i)).toBeInTheDocument()
})
```

---

## Debugging Validation Errors

### Backend Error Response

```json
{
  "error": "1 validation error for HorseCreate\nmicrochip\n  Value error, Microchip must be exactly 15 digits"
}
```

### Frontend Error Display

```tsx
{errors.map(err => (
  <div key={err.field} className="text-red-600 text-sm">
    {err.field}: {err.message}
  </div>
))}
```

---

## Common Pitfalls

❌ **Never define schema in two places** — JSON Schema in `dna/schemas/` is single source of truth  
❌ **Never skip field validation** — Pydantic must match JSON Schema exactly  
❌ **Never allow null for required fields** — Use `Optional` or `nullable` correctly  
❌ **Never change microchip format** — Always 15 digits, numeric only  
❌ **Never bypass schema validation** — Always validate before creating/updating  

---

## Related Files

- **Schemas:** `dna/schemas/*.json`
- **Pydantic models:** `api/models/__init__.py`
- **TypeScript types:** `app/src/types/`
- **Form validation:** `app/src/lib/schemas.ts`

---

## Quick Reference

```bash
# Validate JSON Schema syntax
npx ajv validate -s dna/schemas/horse.json -d test-data.json

# Generate TypeScript types
npx json2ts --input dna/schemas/*.json --output app/src/types/

# Test Pydantic models
cd api && pytest models/ -v
```
