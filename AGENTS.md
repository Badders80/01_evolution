# Evolution — Model & Account Strategy

## Goal
Never get another surprise Vertex bill. Run everything on flat-fee subscriptions. Use Google free tiers only where they exist and are tracked.

## Subscriptions (Flat Fee)
| Provider | Account | Cost | Use For |
|---|---|---|---|
| **Ollama Cloud** | badders80 (primary) | ~USD 20/mo | **Default for ALL text inference** — unlimited, no metering |
| **Ollama Cloud** | badders808 (backup) | ~USD 20/mo | Failover when badders80 rate-limited |
| **Groq** | single key | pay-as-you-go | Whisper transcription fallback + fast chat fallback |
| **FAL.ai** | single key | credit-based | **All image/video generation** — flat predictable billing |

## Google Accounts (Quota-Tracked, Never Default)
| Account | Email | Free Quota | Use For |
|---|---|---|---|
| **Work** | alex@evolutionstables.nz | STT 60 min/mo; Veo 3.1 2 vids/day | Speech-to-text when quota available; Veo only when FAL unavailable and quota exists |
| **Personal** | baddeley0@gmail.com | AI Studio 1500 req/day; STT ~60 min/day | AI Studio chat/image/STT when Ollama down and work STT exhausted |

## Routing Rules (Hardcoded in `model_router.py`)
1. **Text (chat, coding, reasoning):** Ollama Cloud → Groq → error. **Never** Gemini/Vertex.
2. **Email tasks (parse, classify, sentiment):** Groq first (burns free tier) → Ollama fallback. Perfect for weekly batch jobs.
3. **Speech-to-text:** Google STT (work, free quota) → AI Studio STT (personal, free quota) → Groq Whisper ($0.003/min) → error. **Never** Gemini STT.
4. **Image generation:** FAL.ai → AI Studio image (personal, free quota) → error. **Never** Vertex Imagen.
5. **Video generation:** FAL.ai only. **Never** Vertex Veo unless explicit override and quota tracked.
6. **Infrastructure:** Firestore, GCS, Cloud Functions, BigQuery — always work account. No AI inference here.

## Environment Gates
| Variable | Value | Effect |
|---|---|---|
| `GEMINI_API_KEY` | commented out in `~/.env` | Gemini cannot auth even if called |
| `GEMINI_ALLOW_TRANSCRIPTION` | absent / false | `model_router.gemini_transcribe()` raises on any call |
| `GEMINI_ALLOW_TEXT_GENERATION` | absent / false | Any text generation via Gemini raises |
| `AI_STUDIO_ALLOW` | `true` | AI Studio free tier is enabled |
| `AI_STUDIO_API_KEY` | set | Personal account API key for AI Studio |
| `GROQ_API_KEY` | set | Whisper + chat fallback enabled |
| `FAL_API_KEY` | set | Image/video generation enabled |

## Quota Tracking
File: `api/email-ingest/.quota_state.json` (auto-created, daily/monthly buckets)
- `google_stt_free` — 3600 sec/month, resets monthly
- `veo_3_1_work` — 2/day, resets daily
- `ai_studio_chat` — 1500/day, resets daily
- `ai_studio_image` — 1500/day, resets daily
- `ai_studio_stt` — 3600 sec/day, resets daily

Tracker is consumed **after** a successful API call, never before. If a call fails, quota is not burned.

## Account Switching
Ollama Cloud rotation is manual today:
```bash
~/switch_to_badders80.sh      # primary
~/switch_to_badders808.sh    # backup when rate-limited
```
Future: add automatic rotation in `model_router.py` when 429 received.

## Current Status
- ✅ `transcriber.py` — auto engine uses quota tracker (Google → AI Studio → Groq)
- ✅ `reconciler.py` — uses `model_router.chat()` → Ollama Cloud only
- ✅ `trigger_imap.py`, `backfill.py` — engine changed from `gemini` to `auto`
- ✅ `~/.env` — Gemini keys commented out, Groq/FAL/AI Studio active
- ✅ `model_router.py` — `gemini_transcribe()` method fixed (was broken definition)
- ✅ `.quota_state.json` — initialized with zero usage
- 🔄 Next: Add automatic Ollama key rotation; add `gcloud functions deploy` env var audit to ensure no `GEMINI_API_KEY` leaks in Cloud Functions

## What to Never Do
- Never set `engine="gemini"` in any caller.
- Never add `gemini-2.5-pro` or `gemini-2.5-flash` as a fallback in `model_router.py`.
- Never uncomment `GEMINI_API_KEY` in `~/.env` without a budget cap and explicit approval.
- Never deploy a Cloud Function with `GEMINI_API_KEY` in its environment.
