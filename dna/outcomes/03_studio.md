# Extraction Report: Evolution_Studio

**Source:** `/home/evo/workspace/projects/Evolution_Studio`
**Date:** 2026-05-19
**Extraction Role:** Lead Cloud Architect — outcome-driven, ignoring current execution methods

---

## Final Artifacts & Deployment Targets

| Artifact | Description | Target |
|----------|-------------|--------|
| Kingmaker video (MP4) | 5-scene video: Intro → Call → Race → Verdict → Outro | Cloud Storage bucket → Platform delivery |
| Generated images (PNG/WebP) | AI-generated documentary-style horse photos | Cloud Storage bucket |
| Voiceover audio (MP3) | ElevenLabs "Charlie" voice narration | Cloud Storage bucket |
| Investor Update HTML (v2) | Hosted HTML update for email/web | Cloud Storage → Platform `public/` |
| Investor Update HTML (v3) | Gmail-compatible teaser HTML | Cloud Storage → Platform `public/` |
| Publish queue packages | Explicit promotion bundles from Studio → Platform | Firestore collection `publish_queue` |
| Content Factory engine output | Structured content from briefs | Cloud Storage bucket |

---

## Core Tech Stack & Hard Dependencies

| Dependency | Purpose | Notes |
|------------|---------|-------|
| `@fal-ai/client` | Image generation (Flux Pro) | Migrate to Vertex AI Imagen |
| `@google-cloud/vertexai` | Gemini API for text generation | Consolidate as primary AI provider |
| `@google/generative-ai` | Alternative Gemini client | Dual client — consolidate |
| `openai` | Text generation fallback | Legacy — consolidate to Vertex AI |
| `puppeteer` | HTML rendering for video frames | Heavy binary dependency |
| `js-yaml` | Brief/template parsing | For content briefs |
| `googleapis` | Google API integration | For email/Gmail integration |
| Node.js | Runtime | Scripts run via `node src/content-factory/engine.js` |

---

## Environment Variables & Secrets (Keys Only)

| Key | Purpose | Required |
|-----|---------|----------|
| `FAL_API_KEY` | Fal.ai image generation | Yes (migrate to Vertex AI Imagen) |
| `ELEVENLABS_API_KEY` | Voiceover generation | Yes (migrate to Vertex AI Chirp) |
| `GCP_PROJECT` | Google Cloud project ID | Yes |
| `GEMINI_MODEL` | Model name for text generation | Yes |
| `GOOGLE_APPLICATION_CREDENTIALS` | GCP service account key | Yes (production) |
| `OPENAI_API_KEY` | OpenAI fallback | Legacy — remove after consolidation |

---

## Validation & Testing Commands

| Command | What It Validates |
|---------|-------------------|
| `just check` | Placeholder — no real checks defined |
| `npm run content-factory` | Runs the content factory engine |
| `npm test` | **Not defined** — `echo "Error: no test specified" && exit 1` |

**Critical Gap:** Zero automated tests. No linting. No type checking.

---

## Key Business Logic / Pipeline Milestones

1. **Intake** — Receive briefs from `intake/` directory (manual or from Evolution_Content)
2. **Pull Facts** — Fetch horse/owner data from SSOT_Build for content accuracy
3. **Draft** — Generate content drafts using AI (text, image prompts, voiceover scripts)
4. **Review** — Human review and revision in `review/` directory
5. **Approve** — Sign-off recorded in `approved/` directory
6. **Package** — Bundle approved content into publish-ready format in `packages/`
7. **Publish** — Explicit promotion step: copy delivery assets to `Evolution_Platform/public/...`

### Critical Business Rules

- Studio is a **workbench**, not a canonical truth store
- Studio never stores canonical data — only working output
- Publish is an **explicit promotion step**, not automatic
- DNA-compliant branding is mandatory: gold `#d4a964`, black `#121212`, Inter Bold typography
- Kingmaker template: 5-scene video (Intro → Call → Race → Verdict → Outro)
- Investor Update Pipeline has **3 human checkpoints** (no auto-send)
- Ken Burns motion effect and burned-in captions for video
- File-first manual workflow is the default until repeated use reveals minimal useful automation

### Data Flow (Unidirectional)

```
SSOT_Build → Evolution_Studio (horse data for content accuracy)
Evolution_Content → Evolution_Studio (raw content + assets)
Evolution_Studio → Evolution_Platform (delivery copies: videos, HTML updates)
Evolution_Studio → Evolution_CRM (investor update emails)
```

---

## Migration Debt Watch

| Item | Risk | Recommendation |
|------|------|----------------|
| Multiple AI providers (Fal.ai, ElevenLabs, OpenAI, Gemini) | Auth sprawl, inconsistent behavior | Consolidate to Vertex AI (Imagen, Chirp, Gemini) |
| No automated tests | Cannot verify video/image generation pipeline | Add integration tests for each pipeline stage |
| Manual `git push` for publish | Error-prone, not auditable | Replace with Pub/Sub → Cloud Build trigger |
| Local file-based workflow | Not cloud-accessible | Move to Cloud Storage buckets with Firestore metadata |
| Puppeteer for video rendering | Heavy, compute-intensive | Consider Cloud Run with GPU or keep local rendering |
| No CI/CD | Manual deployment only | Add Cloud Build pipeline |
| `npm test` is a no-op | No CI gate | Define real test suite |