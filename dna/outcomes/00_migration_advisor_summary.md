# Migration Advisor Summary: Debt & Drift Watch

**Date:** 2026-05-19
**Purpose:** Ensure the migration from the old workspace to `vertex_workspace` does not carry forward debt, drift, or anti-patterns. This is the watcher document.

---

## Executive Summary

The old workspace has **12 projects** with varying levels of maturity. The new `vertex_workspace` is at **~7% completion** against the full migration scope. The biggest risk is not technical complexity — it's **carrying forward patterns that the audit explicitly identified as anti-patterns.**

This document tracks every piece of debt and drift risk, organized by severity.

---

## 🔴 Critical Debt (Must Fix Before Any Production Deployment)

### 1. No Real `state-api`
- **Old:** `index.js` returns `res.send('Stub state-api')`
- **New:** Same stub exists in `vertex_workspace/index.js`
- **Risk:** The entire agent layer depends on this. If it's a stub, everything is a stub.
- **Fix:** Implement full Firestore-backed CRUD API before building anything else.

### 2. Deprecated AI Model References
- **Old:** `test_gemini.py` uses `gemini-1.0-pro` (retired), `create-function` uses `gemini-1.5-pro-latest` (check deprecation)
- **New:** Same deprecated references exist in `vertex_workspace`
- **Risk:** API calls will fail in production. Gemini 1.5 Flash is already retired.
- **Fix:** Update all model references to `gemini-2.0-flash` or `gemini-2.5-pro`.

### 3. Zero Automated Tests
- **Old:** Evolution_Content, Evolution_Studio, Evolution_Ops, Evolution_Dev have `npm test` returning `exit 1`
- **New:** No tests added in vertex_workspace
- **Risk:** Cannot verify any pipeline works. Silent failures in production.
- **Fix:** Require at least one integration test per Cloud Function before marking it "complete."

### 4. Secrets in `.env` Files
- **Old:** Symlinked `.env` at `/home/evo/.env`, SSOT_Build had secrets committed to git history
- **New:** `.env` file exists at `vertex_workspace` root
- **Risk:** Security incident waiting to happen.
- **Fix:** Move all production secrets to Secret Manager. Never commit `.env`.

### 5. No Firestore Security Rules
- **Old:** No security model documented anywhere
- **New:** No `.rules` file or security model in vertex_workspace
- **Risk:** Any client can read/write any document.
- **Fix:** Define and deploy Firestore security rules before any production data.

---

## � Build Status

**See `15_Build_Status.md`** for a live tracker of what's been built vs what the plan specified.

Current progress: **56 / 76 files (74%)**. The API layer is complete. The Next.js app has public pages, admin dashboard, horse intake, and auth. Missing: admin detail pages for owners/trainers/HLTs/assets, and UI components.

---

## �🟡 Significant Drift (Must Address Before Phase 2)

### 6. Demo-Quality Code in Production Paths
- **Old:** `ingest-function` hardcodes `https://news.google.com/`
- **New:** Same demo code exists in `vertex_workspace/projects/content_engine/functions/ingest/index.js`
- **Risk:** Production pipeline will scrape Google News instead of NZ racing sources.
- **Fix:** Replace with real Puppeteer/Cheerio scrapers for NZ sources.

### 7. Multiple AI Providers
- **Old:** Evolution_Studio uses Fal.ai, ElevenLabs, OpenAI, and Gemini
- **New:** No consolidation plan in vertex_workspace
- **Risk:** Auth sprawl, inconsistent behavior, cost unpredictability.
- **Fix:** Consolidate to Vertex AI (Imagen, Chirp, Gemini). Keep Ollama for local-only tasks.

### 8. SQLite as Production Database
- **Old:** Evolution_Platform, Evolution_Token, Evolution_Content all use SQLite
- **New:** `firestore_schema.json` exists but is basic (4 collections, no relationships)
- **Risk:** No concurrency, no cloud access, no multi-user support.
- **Fix:** Migrate to Firestore for core entities. Consider Cloud SQL for relational data (Token holdings, cap table).

### 9. Manual Deployment Pattern
- **Old:** `git push` from Studio to Platform for investor updates
- **New:** No CI/CD in vertex_workspace. `BLOCKERS.md` lists manual `gcloud` commands.
- **Risk:** Error-prone, not auditable, no rollback.
- **Fix:** Implement Cloud Build + Pub/Sub for all deployments.

### 10. Duplicate `dispatch.js` Files
- **Old:** `Evolution_Dev/dispatch.js` and `vertex_workspace/projects/dev_ops/scripts/dispatch.js`
- **New:** Both exist with slightly different implementations
- **Risk:** Confusion about which is canonical. Divergent behavior.
- **Fix:** Pick one canonical version. Delete the other.

### 11. Scope Confusion in `create_content`
- **Old:** `Evolution_Content/scripts/` has content scrapers; `Evolution_Dev/` has horse scrapers
- **New:** `dev_ops/functions/create_content/` is a horse scraper for `loveracing.nz`; `content_engine/functions/create/` is a generic summarizer
- **Risk:** Wrong function called for wrong purpose.
- **Fix:** Clarify ownership. Rename or merge.

### 12. `ingest_docs.js` is a Simulation Stub
- **Old:** `Evolution_Dev/ingest_docs.js` logs `[SIMULATED] Indexing`
- **New:** Same stub exists in `vertex_workspace`
- **Risk:** Vertex AI Search will never have real data.
- **Fix:** Replace with actual Vertex AI Search API calls.

---

## 🟢 Minor Drift (Address During Phase 3)

### 13. `@evo/dna` Workspace Link
- **Old:** SSOT_Build references `@evo/dna` via `file:../../../../../workspace/DNA`
- **Risk:** Breaks if DNA path changes.
- **Fix:** Package DNA as npm module or copy into each project.

### 14. No Shared Test Infrastructure
- **Old:** Each project has different (or no) test setup
- **Risk:** Inconsistent quality gates.
- **Fix:** Standardize on Vitest + Playwright across all projects.

### 15. No Monitoring or Alerting
- **Old:** Local logs, `MEMORY.md`, `SESSION_LOG.md`
- **Risk:** Silent failures go unnoticed.
- **Fix:** Add Cloud Logging + Cloud Monitoring alerts.

### 16. `just check` is a Placeholder in Some Projects
- **Old:** Evolution_Content and Evolution_Studio have `just check` that just echoes
- **Risk:** No real validation.
- **Fix:** Define real check commands (type-check, lint, test).

### 17. No Input Validation on Cloud Functions
- **Old:** No Pydantic/Joi validation on function inputs
- **New:** `models.py` exists but is not imported by any function
- **Risk:** Garbage in, garbage out.
- **Fix:** Wire Pydantic models into all Cloud Functions.

---

## Agent Layer: Specific Watch Items

The agent layer is the **foundation everything else sits on**. If it's fragile, everything built on top will be fragile.

| Component | Current State | Target State | Priority |
|-----------|---------------|--------------|----------|
| `state-api` | Stub (`res.send('Stub state-api')`) | Firestore-backed CRUD API | 🔴 P0 |
| `dispatch.js` | Basic `gsd-pi` loop, no retry | Poll queue, apply Resource Governor, stream events | 🔴 P0 |
| `manage.js` | Missing from root | CLI: `status`, `dispatch`, `logs --tail` | 🟡 P1 |
| Firestore agent state | Not implemented | `agent_state` collection with task queue | 🔴 P0 |
| Resource Governor | Not implemented | Route tasks to cloud/local models based on DNA v2.0 rules | 🟡 P1 |
| Verification step | Not implemented | Mandatory verification command + output check | 🟡 P1 |
| Bounded context | Not implemented | Task payload includes `workspace` and `files` scope | 🟡 P1 |

---

## Migration Priority Matrix

| Project | Business Criticality | Complexity | New Stack Readiness | Recommended Order |
|---------|---------------------|------------|---------------------|-------------------|
| Evolution_Content | 🟡 Medium | Low | 🟡 Scaffolded | **1st (pilot)** |
| SSOT_Build | 🔴 Critical | Medium | Low (needs UI) | 2nd |
| Evolution_Platform | 🔴 Critical | High | 🔴 None | 3rd |
| Evolution_Token | 🔴 Critical | 🔴 Very High | 🔴 None | 4th (after infra solid) |
| Evolution_Studio | 🟡 Medium | Medium | 🔴 None | 5th |
| Evolution_Ops | 🟡 Medium | Low | 🔴 None | 6th |
| Evolution_CRM | 🟢 Low | Low | 🔴 None | 7th |
| DNA/Shared (pre-evo_01; see new slim central in _shared/dna/) | 🔴 Critical | Low | 🟡 Partial | Parallel with pilot |

---

## Pre-Flight Checklist

Before any code is written in `vertex_workspace`, verify:

- [ ] `state-api` is a real Firestore-backed API (not a stub)
- [ ] All deprecated model references are updated (`gemini-2.0-flash` minimum)
- [ ] At least one integration test exists for the content pipeline
- [ ] Secret Manager is configured (no `.env` in production)
- [ ] Firestore security rules are defined
- [ ] Cloud Build CI/CD is configured
- [ ] `dispatch.js` has retry logic and error handling
- [ ] `manage.js` CLI exists with `status` and `dispatch` commands
- [ ] Resource Governor rules are codified (not just documented)
- [ ] Verification step is mandatory before marking any task "done"

---

## Cross-Reference

| This Document | References |
|---------------|-----------|
| Debt items 1-5 | `MIGRATION_TODO.md` items 1.2, 1.5, 2.2, 2.4, 6.1 |
| Debt items 6-12 | `MIGRATION_TODO.md` items 3.1, 3.5, 7.1-7.7 |
| Agent layer | `AGENTS.md` in vertex_workspace, `Workspace_DNA_v2.0_Specification.md` |
| Priority matrix | `DESIRED_OUTCOMES.md` Migration Priority Matrix |
| Anti-patterns | `MIGRATION_GUIDE.md` §10, `Developer_Workflow_Patterns.md` §8 |