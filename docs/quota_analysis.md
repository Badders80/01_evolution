# GOOGLE CLOUD QUOTA ANALYSIS — Two-Account Exploitation Strategy

## EXECUTIVE SUMMARY

You are paying **$466 NZD in 3 weeks** for one reason: **Vertex AI Gemini 3.5 Flash**. Everything else is essentially free or already-paid. The fix is routing discipline — not a new subscription.

---

## YOUR CURRENT INVENTORY

### PAID FLAT-FEE (UNLIMITED — USE THESE FIRST)

| Service | Accounts | Cost | Best For |
|---------|----------|------|----------|
| **Ollama Cloud** | badders80, badders808 | **Already paid** | All text generation, coding, reasoning, chat, parsing |

### GOOGLE FREE TIER (ZERO COST IF UNDER QUOTA)

| Service | Account 1 (alex@work) | Account 2 (baddeley0@personal) | Combined |
|---------|----------------------|-------------------------------|----------|
| **Speech-to-Text** | 60 min/month | 60 min/month | **120 min/month** |
| **Veo 3.1** | 2 videos/day | unknown (likely 2/day) | **4 videos/day** |
| **Gemini 2.5 Flash (AI Studio)** | 1,500 req/day, 1M tok/min | 1,500 req/day, 1M tok/min | **3,000 req/day** |
| **Gemini 2.5 Pro (AI Studio)** | 50 req/day | 50 req/day | **100 req/day** |

### CHEAP FALLBACKS (PENNIES)

| Service | Cost | Best For |
|---------|------|----------|
| **Groq Whisper** | $0.003/minute | STT when Google free tier exhausted |
| **FAL.ai** | Already have key | All image/video generation |

### THE ONE THING BLEEDING MONEY

| Service | Current Cost | Why |
|---------|-------------|-----|
| **Vertex AI Gemini 3.5 Flash** | **$466 NZD/3 weeks** | Your code and agents were hardcoded to `engine="gemini"` routing through **Vertex AI** (pay-as-you-go, no free tier) instead of **Google AI Studio** (free tier) or Ollama (already paid) |

---

## THE LEAK — ROOT CAUSE

### What You Were Doing (Wrong)

```
Every email transcript → engine="gemini" → Vertex AI Gemini 2.5 Flash → $$$$
Every agent chat → model="gemini-2.5-pro" → Vertex AI → $$$$
Every image → Vertex Imagen (implied) → $$$$
```

### Why It Costs So Much

- **Vertex AI** = enterprise billing, no free tier, per-token pricing
- **Google AI Studio** = consumer/developer free tier, same model (Gemini 2.5 Flash), different API endpoint
- You were hitting the **enterprise endpoint** because your `GEMINI_API_KEY` was a Vertex key, not an AI Studio key

### The $466 Breakdown (from your billing)

| Line Item | Cost |
|-----------|------|
| Vertex AI — Project Evolution-Engine | $466.62 |
| SKU: Gemini 3.5 Flash Global Text Input — Predictions | $263.45 |
| Cloud Storage, Artifact Registry, Functions | ~$0.08 |
| **Total** | **$466.70 NZD** |

**Infrastructure (Firestore, GCS, Functions) is $0.08. The AI is $466.62.**

---

## OPTIMAL ROUTING STRATEGY

### Decision Tree for Every Request

```
REQUEST TYPE?
├── TEXT (emails, parsing, coding, reasoning, chat)
│   ├── Ollama Cloud (badders80) ──→ DEFAULT, UNLIMITED, ALREADY PAID
│   └── Ollama Cloud (badders808) ──→ failover if rate limited
│
├── AUDIO TRANSCRIPTION (trainer videos, race calls)
│   ├── Google STT personal (baddeley0) ──→ 60 min/mo FREE
│   ├── Google STT work (alex) ──→ 60 min/mo FREE
│   ├── Groq Whisper ──→ $0.003/min CHEAP
│   └── Gemini 2.5 Flash (AI Studio FREE) ──→ LAST RESORT
│
├── IMAGE / VIDEO GENERATION
│   ├── FAL.ai ──→ DEFAULT (key already in ~/.env)
│   └── Veo 3.1 ──→ 2/day per account FREE quota only
│
└── INFRASTRUCTURE (Firestore, GCS, Cloud Functions)
    └── Work account (alex) ──→ expected ~$5/mo
```

### The Golden Rule

> **Never touch Vertex AI for text or transcription. It has no free tier and costs 1000x more than the alternatives you already own.**

---

## ACCOUNT-SPECIFIC TACTICS

### PERSONAL ACCOUNT (baddeley0@gmail.com) — THE FREE TIER GOLDMINE

**Current state:** Not linked to any GCP project. No billing. Pure free tier.

**Action:**
1. Create project `evolution-personal` (no billing account needed)
2. Enable **Speech-to-Text API** only
3. Route ALL STT here first — 60 min/month completely free
4. Get AI Studio API key from `aistudio.google.com` — separate from Vertex key
5. Use as Gemini Flash fallback for transcription only (1,500 req/day free)

**Why this matters:** Your work account is currently burning through both STT free tier AND paid Vertex AI. Moving STT to personal gives you **120 min/month combined** and keeps work account for infrastructure only.

### WORK ACCOUNT (alex@evolutionstables.nz) — STOP THE BLEED

**Current state:** Active project `evolution-engine`. Billing account attached. Vertex AI enabled.

**Action:**
1. **Disable Vertex AI billing** or set **hard quota limit at $10 NZD/month**
2. Keep for: Firestore, GCS, Cloud Functions, Veo 3.1 (2/day free)
3. Route STT to personal account first — preserve work account 60 min for overflow
4. Set billing alert at **$50 NZD** — killswitch if anything leaks

---

## CODE CHANGES REQUIRED

| File | Current Leak | Fix |
|------|-------------|-----|
| `transcriber.py` | Falls back to Gemini via `GEMINI_API_KEY` (Vertex) | Change to `GOOGLE_AI_STUDIO_KEY` (free tier) or disable Gemini fallback entirely |
| `trigger_imap.py` | Patched to `engine="auto"` ✅ | Verify it routes to Google STT first, not Gemini |
| `backfill.py` | Comment says "engine=gemini for premium output" | Remove comment, enforce `engine="auto"` |
| `reconciler.py` | Calls Ollama ✅ | Already correct — no change |
| `~/.env` | `GEMINI_API_KEY` maps to Vertex | Add `GOOGLE_AI_STUDIO_KEY` (free tier key), comment out `GEMINI_API_KEY` |

### The Critical `~/.env` Change

```bash
# BEFORE (leaking)
GEMINI_API_KEY=AIzaSy...VertexKey...

# AFTER (locked)
# GEMINI_API_KEY=AIzaSy...VertexKey...  # DISABLED — costs $$$ via Vertex AI
GOOGLE_AI_STUDIO_KEY=AIzaSy...StudioKey...  # FREE TIER — 1500 req/day
OLLAMA_API_KEY=...  # DEFAULT FOR ALL TEXT
GROQ_API_KEY=gsk_...  # STT FALLBACK
FAL_API_KEY=045b...   # IMAGE/VIDEO
```

---

## MONTHLY COST PROJECTION

| Service | Current (Leaking) | Fixed (This Strategy) |
|---------|-------------------|----------------------|
| Vertex AI Gemini | $600+ NZD/mo | **$0** (disabled) |
| Google STT | Unknown (part of $600) | **$0** (120 min free across 2 accounts) |
| Groq Whisper | $0 | ~$2 NZD/mo (only if free tier exhausted) |
| Ollama Cloud | Already paid | Already paid |
| FAL.ai | Already have key | Usage-dependent |
| GCP Infrastructure | ~$5 NZD/mo | ~$5 NZD/mo |
| **TOTAL** | **~$605 NZD/mo** | **~$7 NZD/mo** |

**Savings: $598 NZD/month** — essentially you go from bleeding to nearly free.

---

## RISK: WHAT COULD STILL LEAK

| Risk | Mitigation |
|------|-----------|
| Cron job or background process still calling Gemini | Audit `ps aux` for python processes, check `crontab -l` |
| Other workspace (Evolution_Dev, Studio, Content) hardcoded | Already patched — monitor for regression |
| Someone else with billing access on work account | IAM audit — check who has `roles/billing.admin` |
| AI Studio free tier exhausted (1500/day) | Falls back to Groq ($0.003/min) — still cheap |
| FAL.ai quota exceeded | Falls back to Veo 3.1 (2/day per account) |

---

## IMMEDIATE ACTION CHECKLIST

1. **Get AI Studio key** — go to `aistudio.google.com` with **both** accounts, generate API keys
2. **Comment out `GEMINI_API_KEY`** in `~/.env` — stop all Vertex AI calls
3. **Add `GOOGLE_AI_STUDIO_KEY`** to `~/.env` — enable free Gemini tier
4. **Update `transcriber.py`** — change Gemini fallback to use AI Studio key, not Vertex key
5. **Create personal GCP project** — `gcloud projects create evolution-personal`
6. **Enable Speech-to-Text on personal** — `gcloud services enable speech.googleapis.com --project evolution-personal`
7. **Set billing alert** — $50 NZD on work account
8. **Verify no background leaks** — `ps aux | grep -i gemini`

---

## OPEN QUESTIONS FOR YOU

1. **Do you have an AI Studio key?** (from `aistudio.google.com` — separate from your Vertex key)
2. **Can you confirm personal account has no startup/spark credits?** Sometimes Google gives $300-3000 credits to new accounts
3. **Who else has access to the work billing account?** Could someone else be triggering Vertex AI costs?
4. **Do you want to keep Gemini as a transcription fallback at all?** Groq at $0.003/min is arguably cheaper than managing two API keys

---

*Analysis generated from code audit of `/home/evo/evo_01/01_evolution/api/email-ingest/` and billing data provided.*
