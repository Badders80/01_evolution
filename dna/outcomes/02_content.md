# Extraction Report: Evolution_Content

**Source:** `/home/evo/workspace/projects/Evolution_Content`
**Date:** 2026-05-19
**Extraction Role:** Lead Cloud Architect — outcome-driven, ignoring current execution methods

---

## Final Artifacts & Deployment Targets

| Artifact | Description | Target |
|----------|-------------|--------|
| Scraped content JSON | Raw scraped data from NZ racing sources | Cloud Storage bucket (`vertex-workspace-raw-content`) |
| Structured content JSON | AI-summarized, topic-classified articles | Cloud Storage bucket (`vertex-workspace-structured-content`) |
| Content catalog (NDJSON) | Searchable metadata index of all content | Firestore collection `content_catalog` or Vertex AI Search |
| SQLite ledger | Local structured store for tips, results, scores | Firestore collections (`tips`, `results`, `scores`) |
| Express API (port 3100) | Query interface for assets, tags, collections | Cloud Run service or Cloud Functions |
| Asset Manager UI | Human curation interface for content catalog | Firebase Hosting or lightweight Next.js app |
| Media assets (images, video, audio) | Canonical approved media files | Cloud Storage bucket |

---

## Core Tech Stack & Hard Dependencies

| Dependency | Purpose | Notes |
|------------|---------|-------|
| Express.js | API server | `server.js` on port 3100 |
| better-sqlite3 | Local content ledger | Must migrate to Firestore |
| Playwright | Web scraping (JS-heavy sites) | Headless browser for NZ racing sites |
| `@google-cloud/vertexai` | Gemini API for summarization | Must update model references |
| `@google/genai` | Alternative Gemini client | Dual client — consolidate |
| `@google-cloud/storage` | Cloud Storage uploads | Already GCS-aware |
| `@google-cloud/speech` | Audio transcription | For audio asset processing |
| `ffmpeg-static` + `fluent-ffmpeg` | Audio/video processing | Binary dependency |
| `imap` + `mailparser` | Email ingestion | For email-based content sources |
| `openai` | Alternative AI client | Legacy — consolidate to Vertex AI |
| `multer` | File upload handling | For Asset Manager UI |

---

## Environment Variables & Secrets (Keys Only)

| Key | Purpose | Required |
|-----|---------|----------|
| `PORT` | Express server port (default 3100) | Yes |
| `GCP_PROJECT` | Google Cloud project ID | Yes (for Vertex AI) |
| `GEMINI_MODEL` | Model name for summarization | Yes |
| `GOOGLE_APPLICATION_CREDENTIALS` | GCP service account key path | Yes (production) |
| `FIRECRAWL_API_KEY` | Firecrawl scraper API key | Yes (for cloud scraping) |
| `EMAIL_USER` / `EMAIL_PASS` | Email ingestion credentials | For email sources |
| `OPENAI_API_KEY` | OpenAI API key | Legacy — should be removed |
| `GOOGLE_CLOUD_BUCKET` | Cloud Storage bucket name | Yes |

---

## Validation & Testing Commands

| Command | What It Validates |
|---------|-------------------|
| `just check` | Placeholder — no real checks defined |
| `npm run scrape` | Runs pundit scraper + TAB weekend preview |
| `npm run ingest` | Processes scraped data into ledger |
| `npm run verify` | Data verification script |
| `npm start` | Starts Express API on port 3100 |
| `npm test` | **Not defined** — `echo "Error: no test specified" && exit 1` |

**Critical Gap:** Zero automated tests. This is flagged in the audit as a "critical misalignment."

---

## Key Business Logic / Pipeline Milestones

1. **Scrape** — Daily ingestion from NZ racing sources (NZ Herald Racing, Stuff Racing, Racing.com, TAB, pundit tips)
2. **Ingest** — Transform raw scraped HTML/JSON into structured records in SQLite ledger
3. **Catalog** — Index content into searchable NDJSON catalog with tags and metadata
4. **Serve** — Express API serves queries for assets, tags, and collections
5. **Curate** — Human curation via Asset Manager UI (`assets/index.html`)
6. **Publish** — Approved content flows to Evolution_Studio for production

### Critical Business Rules

- Content flows unidirectionally: `SSOT_Build → Evolution_Studio → Evolution_Content → Evolution_Platform`
- `Evolution_Content` is the canonical library — Studio and Platform are consumers
- `drop/` is the only raw intake surface for new update assets
- Approved assets must have a delivery copy in `Evolution_Platform/public/...` before HTML references them
- File-first, not database-first (v0.0 constraint — NDJSON catalog before Firestore)
- Manual metadata tagging as first classification method (v0.0)

### Data Flow (Unidirectional)

```
External Sources → Evolution_Content (scrape → ingest → catalog)
Evolution_Content → Evolution_Studio (raw content + assets)
Evolution_Content → Evolution_Platform (public content: tips, results, news)
Evolution_Ops → Evolution_Content (TAB results for reconciliation)
```

---

## Migration Debt Watch

| Item | Risk | Recommendation |
|------|------|----------------|
| Zero automated tests | Brittle pipeline, fear of refactoring | Require tests for every Cloud Function before migration |
| SQLite as production store | No concurrency, no real-time, no cloud access | Migrate to Firestore collections |
| Local `media/` storage | Not cloud-accessible, no CDN | Move to Cloud Storage buckets |
| Hardcoded `news.google.com` scraper | Demo-quality, not production | Replace with real Puppeteer/Cheerio scrapers for NZ sources |
| Dual Gemini clients (`@google-cloud/vertexai` + `@google/genai`) | Confusion, auth sprawl | Consolidate to single Vertex AI client |
| `openai` dependency | Legacy, not used for primary flow | Remove |
| No Cloud Scheduler trigger | Manual execution only | Add Cloud Scheduler (07:00 NZT daily) |
| Email ingestion not in new pipeline | Gap in content sources | Add email trigger Cloud Function |
| `npm test` is a no-op | No CI gate | Define real test suite |