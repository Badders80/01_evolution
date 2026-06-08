# Evolution Model & Agent Strategy
**Status:** ACTIVE — replaces all previous defaults
**Goal:** Zero unexpected bills. Flat-fee first, pay-per-use last.

---

## The Hierarchy (Never Violate)

| Priority | Tool | Cost | Use For | Never Use For |
|----------|------|------|---------|---------------|
| **1** | **Ollama Cloud** (badders80 / badders808) | **$20/mo flat** | ALL text tasks: coding, reasoning, agents, content, chat, email ingest analysis | — |
| **2** | **Groq** | **~$0.50/mo** (Whisper) | Speech-to-text transcription (cheap fallback) | Heavy batch transcription (rate limits) |
| **3** | **Google Speech-to-Text** | **FREE tier** | Primary transcription for email ingest | General AI tasks |
| **4** | **FAL.ai** | **Pay-per-use** | ALL image/video generation (Imagen, Veo replacement) | Text tasks |
| **5** | **Gemini/Vertex** | **$$$** | ABSOLUTE LAST RESORT only | Default anything |

---

## Account Split Strategy

### Work Account: `alex@evolutionstables.nz` (Project: evolution-engine)
- **Role:** Infrastructure + limited AI free tier
- **Free quota:** 2× Veo 3.1 videos/day, free image generation (via Gemini API free tier)
- **Use for:** Cloud Functions, Firestore, GCS, Functions hosting
- **AI use:** Only when personal account quota exhausted

### Personal Account: `baddeley0@gmail.com`
- **Role:** AI free tier overflow
- **Free quota:** 60 min/month Speech-to-Text, better general AI credits
- **Use for:** STT overflow, Gemini free tier overflow
- **Switch:** `gcloud auth activate-service-account` or use separate API keys

---

## Concrete Routing Rules

### 1. Email Ingest (transcriber.py)
```python
# Chain — never skip steps
1. Google STT (free tier, work account)
2. Groq Whisper (cheap, handle 429 with retry)
3. Local Canary (offline, zero cost)
4. Gemini (LAST RESORT only — requires explicit env flag)
```

### 2. Code/Reasoning/Agents (All Scripts)
```python
# Default — no exceptions
OLLAMA_MODEL = "ollama/kimi-k2.6:cloud"  # or deepseek-v4-pro:cloud
# Switch script: /home/evo/switch_to_badders80.sh
```

### 3. Image/Video Generation
```python
# FAL.ai only — never Vertex Imagen
FAL_API_KEY = os.getenv("FAL_API_KEY")
# Image: fal-ai/flux-lora / fal-ai/flux-pro
# Video: fal-ai/veo3 / fal-ai/luma-dream-machine
```

### 4. Infrastructure (Cloud Functions, Firestore, GCS)
```python
# Google Cloud — always work account
# No AI predictions through these credentials
```

---

## Cost Guardrails

### Immediate Actions (Done)
- [x] Kill all background `gemini` CLI processes
- [x] Patch email-ingest scripts: `engine="gemini"` → `engine="auto"`
- [x] Patch `.gemini/settings.json`: model → `ollama/kimi-k2.6:cloud`
- [x] Store Groq + FAL keys in `~/.env`

### Required Now
- [ ] **Disable Gemini API key** in `~/.env` (comment out or rename to `GEMINI_API_KEY_BACKUP`)
- [ ] **Add quota tracker** for Google free tiers
- [ ] **Add Groq 429 retry** with exponential backoff
- [ ] **Add daily cost alert** if GCP bill > $5/day

---

## Env Configuration

```bash
# ~/.env — flat-fee first section
OLLAMA_API_KEY=xxx          # badders80 primary
OLLAMA_FALLBACK_MODEL=ollama/deepseek-v4-pro:cloud

# Transcription chain
GROQ_API_KEY=xxx            # cheap STT fallback
GROQ_MODEL=whisper-large-v3

# Image/Video — never Vertex
FAL_API_KEY=xxx             # active FAL credential

# Google Cloud — infrastructure only
GOOGLE_APPLICATION_CREDENTIALS=~/.config/gcloud/application_default_credentials.json

# Gemini — LAST RESORT ONLY (commented by default)
# GEMINI_API_KEY=xxx
```

---

## Verification Commands

```bash
# Check no gemini processes running
ps aux | grep gemini | grep -v grep

# Check Ollama is primary
ollama list | head -5

# Check active gcloud account (should be work)
gcloud config get-value account

# Check daily GCP spend
gcloud billing accounts list  # find billing account
gcloud billing budgets list  # if any set
```

---

## When to Use What (Cheat Sheet)

| Task | Tool | Account | Why |
|------|------|---------|-----|
| Write code | Ollama | badders80 | Unlimited, flat fee |
| Review code | Ollama | badders80 | Unlimited, flat fee |
| Email analysis | Ollama | badders80 | Unlimited, flat fee |
| Transcribe audio | Google STT → Groq | Work → Groq | Free tier first, cheap fallback |
| Generate image | FAL.ai | — | Replaces Vertex Imagen |
| Generate video | FAL.ai | — | Replaces Veo |
| Deploy function | gcloud | Work | Infrastructure |
| Store horse data | Firestore | Work | Infrastructure |
| Upload image | GCS | Work | Infrastructure |

---

**Rule:** If Ollama Cloud can do it, Ollama Cloud does it. Google Cloud is pipes, not brains.
