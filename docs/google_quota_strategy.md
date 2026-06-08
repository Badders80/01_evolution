# Google Cloud Quota Strategy — Two Account Max Exploitation

## Current State

| Account | Role | Billing Status | Risk |
|---------|------|---------------|------|
| **alex@evolutionstables.nz** | Work / GCP project owner | **Burning $466 NZD/3 weeks** | Vertex AI Gemini 3.5 Flash is the leak |
| **baddeley0@gmail.com** | Personal / untapped | Unknown — likely has free tiers sitting unused | No billing account linked yet = pure free tier |

## The Leak

Your $466 charge is **100% Vertex AI Predictions** — SKU `Gemini 3.5 Flash Global Text Input`.

The problem: your code and agents were hardcoded to `engine="gemini"` and `model="gemini-2.5-pro"`, routing everything through **Vertex AI** (pay-as-you-go, no free tier) instead of using the free alternatives you already pay for.

## What You Actually Have (Free/Cheap)

### 1. Ollama Cloud — Paid Flat Fee (UNLIMITED WORKHORSE)
- **badders80** (primary) + **badders808** (backup)
- **Cost:** Already paid. Unlimited tokens.
- **Use for:** All text generation, coding, reasoning, chat, email parsing, reconciliation.
- **Models:** kimi-k2.6:cloud, qwen3.5:cloud, deepseek-v4-pro:cloud
- **Rule:** DEFAULT EVERYTHING HERE. Never use Gemini for text if Ollama is up.

### 2. Google Cloud Speech-to-Text — FREE TIER
- **60 minutes/month per account**
- **2 accounts = 120 minutes/month total**
- **Cost:** $0.00 if under quota
- **Use for:** All audio transcription first attempt
- **Account priority:** Personal (baddeley0) first → Work (alex) second → Groq fallback

### 3. Google AI Studio (Gemini API) — FREE TIER
- **Gemini 2.5 Flash:** 1,500 requests/day, 1M tokens/minute (free)
- **Gemini 2.5 Pro:** 50 requests/day (free)
- **Key difference:** This is **NOT Vertex AI**. Different API endpoint, different quota, zero cost if under limits.
- **Use for:** Video transcription ONLY when STT free tiers exhausted. Never for text/chat.
- **Requirement:** Separate API key from `aistudio.google.com` — NOT the same as GEMINI_API_KEY for Vertex

### 4. Groq Whisper — CHEAP FALLBACK
- **$0.003/minute** (essentially free)
- **Use for:** STT when Google free tier exhausted and Gemini AI Studio rate-limited
- **Current issue:** Rate limit (429) handling missing in transcriber.py

### 5. FAL.ai — PAID FOR IMAGE/VIDEO
- **Already have API key in ~/.env**
- **Use for:** ALL image generation, video generation, product shots
- **Never use:** Vertex Imagen, Vertex Veo (costly)

### 6. Veo 3.1 — FREE DAILY QUOTA (Work Account Only)
- **2 videos/day** on alex@evolutionstables.nz
- **Use for:** Branded content ONLY when FAL.ai can't match the style
- **Track:** Count daily usage to avoid falling into paid tier

## The Strategy

```
TEXT GENERATION (emails, parsing, reasoning, coding)
├── Ollama Cloud (badders80) — DEFAULT, UNLIMITED
└── Ollama Cloud (badders808) — failover if rate limited

AUDIO TRANSCRIPTION (trainer videos, race calls)
├── Google STT personal (baddeley0) — 60 min/mo FREE
├── Google STT work (alex) — 60 min/mo FREE
├── Groq Whisper — $0.003/min CHEAP
└── Gemini 2.5 Flash (Google AI Studio FREE tier) — LAST RESORT

IMAGE / VIDEO GENERATION
├── FAL.ai — DEFAULT (key already in ~/.env)
└── Veo 3.1 (work account) — 2/day FREE quota only

INFRASTRUCTURE (Firestore, GCS, Functions)
└── Work account (alex) — expected cost, minimal
```

## Account-Specific Actions

### Personal Account (baddeley0@gmail.com) — EXPLOIT FREE TIER
1. **Link to gcloud:** `gcloud auth login baddeley0@gmail.com`
2. **Create project:** `gcloud projects create evolution-personal`
3. **Enable APIs:** Speech-to-Text only (disable Vertex AI billing entirely)
4. **Route STT here first** — 60 min/mo free before touching work account

### Work Account (alex@evolutionstables.nz) — STOP THE BLEED
1. **Remove Vertex AI default** — never call Gemini without explicit override
2. **Keep for:** Firestore, GCS, Cloud Functions, Veo 3.1 (2/day only)
3. **Set billing alert:** $50 NZD hard stop
4. **Audit IAM:** ensure no other scripts/services have GEMINI_API_KEY

## What to Change in Code

| File | Current | Fix |
|------|---------|-----|
| `transcriber.py` | `engine="auto"` defaults to Google STT work account only | Add account rotation: personal STT → work STT → Groq → Gemini AI Studio |
| `reconciler.py` | Calls Ollama | ✅ Already correct |
| `trigger_imap.py` | Patched to `engine="auto"` | ✅ Done |
| `backfill.py` | Still has `engine="gemini"` comment | Remove comment, enforce `engine="auto"` |
| `~/.env` | GEMINI_API_KEY for Vertex | Add GOOGLE_AI_STUDIO_KEY (free tier), keep GEMINI as last-resort only |

## Monthly Budget Projection

| Service | Current (Leaking) | Fixed (This Strategy) |
|---------|-------------------|----------------------|
| Vertex AI Gemini | $466 NZD/mo | $0 (disabled) |
| Google STT | Unknown | $0 (120 min free across 2 accounts) |
| Groq Whisper | $0 | ~$2 NZD/mo (if free tier exhausted) |
| Ollama Cloud | Already paid | Already paid |
| FAL.ai | Already paid | Already paid |
| GCP Infrastructure | ~$5 NZD/mo | ~$5 NZD/mo |
| **TOTAL** | **~$471 NZD/mo** | **~$7 NZD/mo** |

## Next Steps

1. **Confirm personal account free tier** — log in baddeley0@gmail.com to Google AI Studio, grab free API key
2. **Build account-aware router** — track STT minutes per account, auto-failover
3. **Add Groq 429 retry** — exponential backoff in transcriber.py
4. **Set billing alert** — $50 NZD on work account
5. **Comment out GEMINI_API_KEY** from default ~/.env exports
