# Extraction Report: Shared Infrastructure & DNA

**Source:** `/home/evo/workspace/` (workspace-level), `/home/evo/workspace/projects/PROJECTS_RULES.md`, DNA layer
**Date:** 2026-05-19
**Extraction Role:** Lead Cloud Architect — outcome-driven, ignoring current execution methods

---

## Final Artifacts & Deployment Targets

| Artifact | Description | Target |
|----------|-------------|--------|
| Shared `.env` file | Central secrets management (symlinked to each project) | Secret Manager (production) |
| `PROJECTS_RULES.md` | Cross-project dependency and build rules | Firestore document or shared config |
| DNA design system | Brand guidelines, voice system, conventions, skills | Cloud Storage + Firestore `dna` collection |
| `CLAUDE.md` | Workspace-level instructions | Migrate to `AGENTS.md` in vertex_workspace |
| `DESIGN.md` | Baseline design specification | Migrate to `projects/dna/` in vertex_workspace |
| `SPRINTS.md` | Sprint tracking | Firestore `sprints` collection |
| `tokens.json` | Token configuration | Firestore `tokens` collection |

---

## Core Tech Stack & Hard Dependencies

| Dependency | Purpose | Notes |
|------------|---------|-------|
| Node.js 20 | Runtime version | Enforced across all projects |
| npm/pnpm | Package manager | Project-specific, documented in `rules.md` |
| Git | Version control | All projects are Git repos |
| Just | Task runner | Every project has a `Justfile` with `just check` |
| `.env` symlink | Central secrets | One `.env` at `/home/evo/.env`, symlinked into each project |

---

## Environment Variables & Secrets (Keys Only)

| Key Pattern | Purpose | Scope |
|-------------|---------|-------|
| `STRIPE_*` | Stripe payment keys | Platform, Token |
| `NEXTAUTH_*` | Authentication secrets | Platform, Token |
| `GCP_PROJECT` | Google Cloud project ID | All GCP projects |
| `GOOGLE_APPLICATION_CREDENTIALS` | GCP service account key | All GCP projects |
| `GEMINI_MODEL` | Default AI model | Dev, Content, Studio |
| `FAL_API_KEY` | Fal.ai image generation | Studio |
| `ELEVENLABS_API_KEY` | Voiceover generation | Studio |
| `OPENAI_API_KEY` | OpenAI fallback | Content, Studio |
| `FIRECRAWL_API_KEY` | Web scraping | Content |
| `OLLAMA_BASE_URL` | Local Ollama endpoint | Dev |
| `DATABASE_PATH` | SQLite database path | Platform, Token |
| `RESEND_API_KEY` | Email delivery | Platform |

---

## Validation & Testing Commands

| Command | What It Validates |
|---------|-------------------|
| `just check` | Universal health check (project-specific) |
| `just dev` | Start development server |
| `just build` | Production build |
| `just clean` | Clean build artifacts |

**Every project must have a `Justfile` with at least `check`, `dev`, `build`, `clean`.**

---

## Cross-Project Dependency Map

```
SSOT_Build ──→ Evolution_Platform (marketplace payload)
SSOT_Build ──→ Evolution_Token (HLT data for tokenization)
SSOT_Build ──→ Evolution_CRM (owner/investor data)
SSOT_Build ──→ Evolution_Studio (horse data for content accuracy)

Evolution_Content ──→ Evolution_Studio (raw content + assets)
Evolution_Content ──→ Evolution_Platform (public content)

Evolution_Studio ──→ Evolution_Platform (delivery copies)
Evolution_Studio ──→ Evolution_CRM (investor update emails)

Evolution_Token ──→ Evolution_CRM (investor data, KYC status)
Evolution_Token ──→ Evolution_Ops (financial data)

Evolution_Platform ──→ Evolution_CRM (lead capture)

Evolution_Ops ──→ Evolution_CRM (investor financial history)

DNA ──→ All projects (brand, conventions, skills)
```

---

## Migration Debt Watch

| Item | Risk | Recommendation |
|------|------|----------------|
| Symlinked `.env` file | Secrets committed to git history (SSOT_Build incident) | Move to Secret Manager for production |
| No shared package for DNA | `@evo/dna` uses `file:` workspace link | Package as npm module or copy into each project |
| No CI/CD pipeline | All deployment is manual | Add Cloud Build for every project |
| No shared test infrastructure | Each project has different (or no) test setup | Standardize on Vitest + Playwright |
| No Firestore security rules | Data exposure risk | Define and deploy before any production data |
| No monitoring or alerting | Silent failures across all projects | Add Cloud Logging + Cloud Monitoring |
| `PROJECTS_RULES.md` not enforced | Rules exist but aren't validated | Add CI checks for rule compliance |