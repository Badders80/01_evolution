# Extraction Report: Evolution_Own

**Source:** `/home/evo/workspace/projects/Evolution_Own`
**Date:** 2026-05-19
**Extraction Role:** Lead Cloud Architect — outcome-driven, ignoring current execution methods

---

## Final Artifacts & Deployment Targets

| Artifact | Description | Target |
|----------|-------------|--------|
| Equity listing schema | Standardised format for NZ racehorse syndication listings | Firestore collection `equity_listings` |
| Market research reports | NZ syndicator landscape analysis | Document storage |
| Scraped syndicator data | Horse availability, pricing, transparency ratings | Firestore collection `market_data` |

---

## Core Tech Stack & Hard Dependencies

| Dependency | Purpose | Notes |
|------------|---------|-------|
| Scraping tools | Market data collection | Scripts in `scraping/` directory |
| `.env` (symlinked) | API keys for scraping | Shared workspace env |

**This project is primarily research and schema design.** Minimal code, mostly documents and scraped data.

---

## Environment Variables & Secrets (Keys Only)

| Key | Purpose | Required |
|-----|---------|----------|
| Various scraping API keys | Web scraping tools | Yes (for data collection) |

---

## Validation & Testing Commands

| Command | What It Validates |
|---------|-------------------|
| None | No build or test commands defined |

---

## Key Business Logic / Pipeline Milestones

1. **Market Research** — Map the NZ racehorse syndication market (13+ syndicators)
2. **Equity Schema Design** — Define standardised equity listing format (price per 1%)
3. **Data Collection** — Scrape syndicator websites for horse availability and pricing
4. **Schema Validation** — Ensure listings are comparable regardless of share size

### Critical Business Rules

- Standardisation unit is "price per 1%" — makes every listing comparable
- Equity CTA is "Register Interest" (ownership requires owner approval)
- GST handling: `gstInclusive` boolean flag
- Estimated pricing is flagged with disclaimer

### Data Flow

```
Evolution_Own → SSOT_Build (equity listing schema for HLT terms)
Evolution_Own → Evolution_Token (market data for pricing)
Evolution_Own → Evolution_Platform (listing format for marketplace)
```

---

## Migration Debt Watch

| Item | Risk | Recommendation |
|------|------|----------------|
| No structured data store | Markdown files and scraped data | Migrate to Firestore `market_data` collection |
| No automated scraping | Manual data collection | Add Cloud Scheduler + Cloud Function for periodic scraping |
| No schema enforcement | Schema defined in docs only | Implement Pydantic/JSON Schema validation |
| No tests | Nothing to test yet | Define test requirements when building the data pipeline |