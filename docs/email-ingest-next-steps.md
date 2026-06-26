# Email Ingest — Next Steps

**Date:** 2026-06-24
**Status:** Local-first pipeline operational. Gmail API is the primary email path. 4 Prudentia transcripts produced locally. Cloud sync is a future enhancement, not a blocker.

## Current State
- 4 transcript JSONs in `api/email-ingest/output/` (now copied to `_assets/horses/prudentia/transcripts/`)
- **Gmail API is the primary email path** (`trigger_gmail.py` + `gmail_client.py`) — uses service account with domain-wide delegation
- IMAP (`trigger_imap.py`) is the legacy fallback — was used to produce the initial transcripts before the Gmail API path was built
- Gmail API credentials need to be restored to `/home/evo/secrets/gmail-service-account.json` (currently missing)
- Pipeline runs **local-first**: transcripts save to `output/` + local SQLite ledger + NDJSON catalog. Cloud APIs (SSOT/Assets) are optional — when they fail, local mock IDs are used and the pipeline continues
- Cloud Function NOT deployed, Cloud Scheduler NOT set up (future enhancement, not blocking)

## To Pick Up Later
1. Restore Gmail service account credentials to `/home/evo/secrets/` — re-enables the primary email path
2. Backfill: push the 4 existing Prudentia transcripts to Firestore via SSOT API (when cloud auth is sorted)
3. Deploy Cloud Function (`just deploy-email-ingest`) — for automated twice-daily runs instead of manual local triggers
4. Set up Cloud Scheduler (`just setup-email-scheduler`) — pairs with Cloud Function deployment
5. Consider: should transcripts also go to other horses? (Only Prudentia has email updates so far)
6. Normalize transcript filenames — dedup `transcript_: Prudentia` vs `transcript_Prudentia` inconsistency
7. Decide transcript format for knowledge repo — JSON references or markdown indexing

## Pipeline Architecture

The email-ingest pipeline at `api/email-ingest/main.py` is designed as a Cloud Function (triggered twice daily, 09:00/21:00 NZST) but currently runs locally via `trigger_gmail.py`. The 8-step pipeline per email:

1. **Fetch** unread emails from `info@wexfordstables.co.nz` via Gmail API (service account + domain-wide delegation)
2. **Parse** email → extract horse name, content date, video URL
3. **Dedup** — checks SSOT `/content` by `source_email_id` (Gmail message ID)
4. **Resolve horse** — queries SSOT `/horses`, name match → microchip (local fallback for Prudentia)
5. **Download video** from CDN URL to temp file
6. **Upload video** to GCS via Assets API `/upload` (falls back to local mock ID if auth fails)
7. **Transcribe** via Google STT → AI Studio → Groq Whisper (quota-aware fallback chain)
8. **Store transcript** via SSOT API `POST /content` (falls back to local mock ID + SQLite + NDJSON if auth fails)

**Local-first design:** Every cloud API call has a local fallback. The pipeline never hard-fails on auth issues — it logs the failure, uses a mock ID, and continues. Transcripts always land in `output/` and the local SQLite ledger.

**What it stores (SSOT content payload):**
- `content_type`: "transcript"
- `horse_microchip`: resolved microchip
- `title`: email subject
- `content_date`: from email
- `speakers`: [{name, label}] — e.g. Andrew Scott, Lance O'Sullivan
- `full_text`: full transcript text
- `segments`: [{start_time, end_time, speaker, text}]
- `source`: transcription engine used
- `source_email_id`: Gmail message ID (dedup key)
- `asset_ids`: [asset_id] from GCS upload
- `status`: "published"

## Local Output Files

5 transcript JSON files in `api/email-ingest/output/` — all Prudentia:

| Date | File | Engine | Quality |
|------|------|--------|---------|
| 2026-05-25 | `transcript_Prudentia_2026-05-25.json` | gemini-2.5-flash | Clean, 4 segments |
| 2026-05-28 | `transcript_Prudentia_2026-05-28.json` | gemini-2.5-flash | Clean, 5 segments |
| 2026-06-02 | `transcript_Prudentia_2026-06-02.json` | gemini-2.5-flash | Clean, 5 segments |
| 2026-06-10 | `transcript_Prudentia_2026-06-10.json` | gemini-flash-latest | Clean, 11 segments |
| 2026-06-10 | `transcript_Audio Update: Prudentia_2026-06-10.json` | gemini-2.5-flash | **Degraded** (excluded from copy) |

## Email HTML Exports (in `_assets/updates/`)

| Date | File | Type |
|------|------|------|
| 2026-05-27 | `Prudentia_Update_27May2026.mp4` | Video |
| 2026-05-28 | `Prudentia_28May2026_email.html` | Email HTML |
| 2026-05-28 | `Prudentia_Update_28May2026.html` | Rendered update |
| 2026-05-28 | `Prudentia_Update_28May2026_email.html` | Email HTML |
| 2026-06-02 | `prudentia_update_02june2026.html` | Rendered update |
| 2026-06-02 | `prudentia_update_02june2026_email.html` | Email HTML |
| 2026-06-10 | `prudentia_update_10june2026.html` | Rendered update |
| 2026-06-10 | `prudentia_update_10june2026_email.html` | Email HTML |

## Key Files

| File | Purpose |
|------|---------|
| `api/email-ingest/main.py` | Cloud Function entry point (for future deployment) |
| `api/email-ingest/gmail_client.py` | Gmail API wrapper (service account + domain-wide delegation) |
| `api/email-ingest/trigger_gmail.py` | **Primary local trigger** — Gmail API path (needs credentials restored) |
| `api/email-ingest/trigger_imap.py` | Legacy IMAP trigger — produced initial transcripts, now superseded |
| `api/email-ingest/parser.py` | Email parser (horse name, date, video URL extraction) |
| `api/email-ingest/transcriber.py` | Multi-engine transcription (Google STT → AI Studio → Groq Whisper) |
| `api/email-ingest/reconciler.py` | LLM-based transcript correction via Ollama |
| `api/email-ingest/corrections.py` | Regex-based domain corrections (horse names, venues, people) |
| `api/email-ingest/model_router.py` | Quota-aware engine routing (Ollama Cloud default, Google gated) |
| `api/email-ingest/output/` | Local transcript JSON output |
| `api/email-ingest/.quota_state.json` | Quota tracking for STT engines |
| `api/email-ingest/knowledge-base.json` | Domain entities for LLM reconciliation (horses, venues, people) |
| `docs/SSOT_AUTH_ISSUE.md` | Documents the 401 auth issue (reference only — local fallbacks bypass this) |

## Decision Points

1. **Transcript format** — the JSON files have `full_text`, `segments`, `speakers`. Should these be indexed in the knowledge repo as markdown, or kept as JSON references?
2. **Other horses** — only Prudentia has email updates. When other horses start racing, the pipeline will need to handle multiple horses.
3. **Cloud deployment timing** — the local-first pipeline works now. Cloud Function + Scheduler is an automation upgrade, not a blocker. Deploy when the volume of emails makes manual triggering impractical.