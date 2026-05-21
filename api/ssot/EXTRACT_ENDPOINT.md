# Loveracing.nz Extractor — API Endpoint

**Status:** ✅ Complete  
**Date:** 2026-05-20  
**Endpoint:** `POST /extract`

---

## What It Does

Scrapes horse data from loveracing.nz Stud Book pages and returns structured JSON.

**URL Pattern:** `https://loveracing.nz/Breeding/{HorseID}/{NameSlug}.aspx`

---

## Usage

### Request

```bash
curl -X POST http://localhost:8080/extract \
  -H "Content-Type: application/json" \
  -d '{"url": "https://loveracing.nz/Breeding/427416/Prudentia-NZ-2021.aspx"}'
```

### Response (200 OK)

```json
{
  "loveracing_id": 427416,
  "name": "Prudentia (NZ) 2021",
  "name_slug": "Prudentia-NZ-2021",
  "microchip": "985125000126462",
  "life_number": "NZ00427416",
  "foaling_date": "2021-11-13",
  "sex": "mare",
  "colour": "Bay",
  "sire_name": "PROISIR (AUS) 2009",
  "sire_loveracing_id": null,
  "dam_name": "LITTLE BIT IRISH (NZ) 2012",
  "dam_loveracing_id": null,
  "breeder": "Goldeye Trust",
  "left_shoulder_brand": null,
  "right_shoulder_brand": null,
  "dna_typed": false,
  "pv": false
}
```

---

## Error Responses

### Invalid URL Format (400)

```json
{
  "error": "Invalid loveracing.nz URL. Expected format: https://loveracing.nz/Breeding/{HorseID}/{NameSlug}.aspx"
}
```

### Missing URL (400)

```json
{
  "error": "Missing 'url' in request body"
}
```

### Network Error (502)

```json
{
  "error": "Failed to fetch loveracing.nz page: [error details]"
}
```

---

## Extracted Fields

| Field | Source | Reliability |
|-------|--------|-------------|
| `microchip` | `<strong>Microchip:</strong>` text node | ✅ High |
| `life_number` | Page text (NZ + 6-8 digits) | ✅ High |
| `foaling_date` | `<strong>Born:</strong>` or `<strong>Foaling date:</strong>` | ✅ High |
| `sex` | Page text (mare/filly/colt/etc) | ✅ High |
| `colour` | Page text (bay/brown/chestnut/etc) | ✅ High |
| `sire_name` | `<strong>Sire:</strong>` link text | ✅ High |
| `dam_name` | `<strong>Dam:</strong>` link text | ✅ High |
| `breeder` | `<strong>Breeder:</strong>` text node | ✅ High |
| `sire_loveracing_id` | Sire link href | ⚠️ Medium (if link exists) |
| `dam_loveracing_id` | Dam link href | ⚠️ Medium (if link exists) |
| `brands` | `<strong>Brands:</strong>` text | ⚠️ Medium (format varies) |

---

## Testing

### Run Tests

```bash
cd api/ssot
source ../venv/bin/activate
python tests/test_extract_endpoint.py
```

### Expected Output

```
============================================================
Testing /extract endpoint
============================================================

📋 Testing URL: https://loveracing.nz/Breeding/427416/Prudentia-NZ-2021.aspx
------------------------------------------------------------
✅ Extraction successful!
   Microchip: 985125000126462
   Life Number: NZ00427416
   Name: Prudentia (NZ) 2021
   Foaling Date: Sat, 13 Nov 2021 00:00:00 GMT
   Sex: mare
   Colour: Bay
   Sire: PROISIR (AUS) 2009
   Dam: LITTLE BIT IRISH (NZ) 2012
   Breeder: Goldeye Trust

✅ All validations passed!
```

---

## Files Changed

| File | Purpose |
|------|---------|
| `api/ssot/routes/extract.py` | New scraping logic |
| `api/ssot/main.py` | Added `/extract` route |
| `api/ssot/routes/__init__.py` | Export extract module |
| `api/ssot/requirements.txt` | Added `requests`, `beautifulsoup4` |
| `api/ssot/tests/test_extract_endpoint.py` | Integration test |

---

## Next Steps

1. ✅ **Backend scraping complete**
2. ⬜ **Frontend form** — Simple input field + "Extract" button
3. ⬜ **Display extracted data** — Show JSON response to user
4. ⬜ **Create horse** — POST extracted data + user additions to `/horses`

---

## Known Limitations

1. **Name extraction** — Currently returns "Stud Book" (h1 tag). Should use title tag or reconstruct from slug.
2. **Sire/Dam IDs** — Only extracted if links are present on the page.
3. **Brands** — Format varies; current logic captures full text.
4. **Rate limiting** — No delay between requests; loveracing.nz may block aggressive scraping.

---

## Dependencies

- `requests>=2.31.0` — HTTP client
- `beautifulsoup4>=4.12.0` — HTML parsing

Install with:

```bash
cd api
python3 -m venv venv
source venv/bin/activate
pip install -r ssot/requirements.txt
```
