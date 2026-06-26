# Email Ingest Pipeline

Fetches Wexford Stables emails, extracts video updates, transcribes them, and stores transcripts locally.

## Architecture

```
IMAP / Gmail API
    ↓
parse_email() → extract horse name, date, video URL
    ↓
resolve_horse_microchip() → local fallback (Prudentia = 985125000126462)
    ↓
if video URL:
    download → transcribe (Groq / Google STT / AI Studio) → save JSON
else:
    store text-only (race acceptances, newsletters)
    ↓
SQLite ledger + NDJSON catalog (local-first, no cloud required)
```

## Scripts

| Script | Purpose |
|--------|---------|
| `trigger_imap.py` | Fetch **latest** matching email via IMAP (single email) |
| `batch_ingest.py` | Fetch **multiple** emails by subject pattern + date range |
| `trigger_gmail.py` | Gmail API variant (requires service account credentials) |
| `parser.py` | Regex-based email body parser (horse name, date, video URL, speakers) |
| `transcriber.py` | Multi-engine transcription: Google STT → Groq Whisper → Canary |
| `main.py` | Shared helpers (video download) |
| `models.py` | Pydantic models (ParsedEmail, TranscriptResult) |
| `corrections.py` | Post-transcription dictionary corrections |
| `reconciler.py` | LLM-based consensus reconciliation across multiple STT engines |

## Usage

### Single email (latest)
```bash
cd 01_evolution
source .venv/bin/activate
python3 api/email-ingest/trigger_imap.py
```

### Batch (multiple emails by subject + date range)
```bash
python3 api/email-ingest/batch_ingest.py
```
Edit `subject_patterns` and `date_start`/`date_end` in `main()` to target specific emails.

### Gmail API (target state, currently blocked by org policy)
```bash
python3 api/email-ingest/trigger_gmail.py
```
Requires: `~/secrets/gmail-service-account.json` + domain-wide delegation.

## Data Paths (local-first)

| Path | Contents |
|------|----------|
| `data/ledger.sqlite` | SQLite ledger — one row per ingested email |
| `data/content-index.ndjson` | NDJSON catalog — append-only event log |
| `output/transcript_{horse}_{date}.json` | Full transcript JSON with segments |

Override with env vars: `INGEST_DB_PATH`, `INGEST_NDJSON_PATH`

## Environment Variables

Required in `~/.env`:
```
WEXFORD_EMAIL_USER=alex@evolutionstables.nz
WEXFORD_APP_PASSWORD=<gmail app password>
GROQ_API_KEY=<groq key for Whisper fallback>
AI_STUDIO_API_KEY=<ai studio key>
```

Optional:
```
SPEECH_TEMP_BUCKET=<gcs bucket for google stt>
CANARY_URL=http://127.0.0.1:5005/transcribe
```

## Transcription Engines

Priority order (when `engine="auto"`):
1. **Google Speech-to-Text** — best quality, requires `gcloud auth application-default login`
2. **AI Studio** (Gemini) — free tier, requires `AI_STUDIO_API_KEY`
3. **Groq Whisper** — fast fallback, requires `GROQ_API_KEY`
4. **NVIDIA Canary** — local GPU daemon, requires `CANARY_URL`

When Google STT auth fails, use `engine="groq"` directly (see `batch_ingest.py`).

## LLM Models (text inference / reconciliation)

Text inference (transcript reconciliation, email parsing assistance) uses Ollama Cloud:

| Role | Model | Notes |
|------|-------|-------|
| Primary | `glm-5.2` | Fast, reliable for text + JSON |
| Fallback | `deepseek-v4-flash` | Quick verification pass |

**Dual subscription support:** Two Ollama Cloud accounts (badders80 primary, badders808 backup) are auto-loaded from `~/.hermes/.env`. If the primary key returns 401, the router automatically rotates to the backup key before failing.

Config: API keys auto-loaded from `~/.hermes/.env`. Endpoint: `https://ollama.com/v1` (OpenAI-compatible). Override models via `OLLAMA_MODEL` / `OLLAMA_FALLBACK_MODEL` env vars.

**Note:** `OLLAMA_FALLBACK_MODEL` in `~/.env` is currently set to `qwen3:30b-a3b` (a local model). This overrides the code default `deepseek-v4-flash`. To use the Cloud fallback, change it to `deepseek-v4-flash` or remove the line.

Voice transcription is handled by Groq (Whisper) and Gemini (AI Studio) — no Ollama Cloud models involved for audio.

## Current State (2026-06-24)

- ✅ IMAP path working (app password auth)
- ✅ Groq Whisper transcription working
- ✅ Batch ingest tested — 4 emails processed (2 video + 2 race acceptance)
- ⏸️ Gmail API blocked by GCP org policy (`constraints/iam.disableServiceAccountKeyCreation`)
- ⏸️ Google STT needs `gcloud auth application-default login` re-auth
- ⚠️ Canary daemon not running (local GPU, optional)