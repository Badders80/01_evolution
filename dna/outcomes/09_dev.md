# Extraction Report: Evolution_Dev (Agent Infrastructure)

**Source:** `/home/evo/workspace/projects/Evolution_Dev`
**Date:** 2026-05-19
**Extraction Role:** Lead Cloud Architect — outcome-driven, ignoring current execution methods

---

## Final Artifacts & Deployment Targets

| Artifact | Description | Target |
|----------|-------------|--------|
| `dispatch.js` | Headless GSD orchestrator — polls for tasks, executes via `gsd headless auto --json` | Cloud Function or Cloud Run |
| `manage.js` | CLI interface for task queueing and status checking | Local CLI tool |
| `state-api` (index.js) | Cloud Function for agent state persistence | Cloud Function `state-api` |
| `models.py` | Pydantic data models (Horse, User, Investment, Lead) | Shared library for Cloud Functions |
| `vertex_pipeline.json` | Vertex AI Pipeline definition (ingest → create → publish) | Vertex AI Pipelines |
| `ingest_docs.js` | Vertex AI Search document ingestion (currently simulation stub) | Cloud Function |
| `linter.js` | Code linting tool | CI/CD pipeline |
| `search.js` | Search utility | TBD |
| `hello.js` | Smoke test | Development only |

---

## Core Tech Stack & Hard Dependencies

| Dependency | Purpose | Notes |
|------------|---------|-------|
| Node.js | Runtime for dispatch, manage, state-api | |
| Python 3 | Runtime for models.py | Pydantic models |
| `dotenv` | Environment variable loading | |
| `eslint` | Code linting | |
| `@google-cloud/firestore` | Firestore client | **Missing from package.json** — critical gap |
| `@google-cloud/functions-framework` | Cloud Functions framework | **Missing from package.json** — critical gap |
| `@google-cloud/storage` | Cloud Storage client | Not in package.json |
| `@google-cloud/vertexai` | Vertex AI client | Not in package.json |
| GSD (General Software Development) | Agent execution framework | External dependency — `gsd headless auto --json` |
| Ollama | Local AI model runtime | For reasoning tasks |

---

## Environment Variables & Secrets (Keys Only)

| Key | Purpose | Required |
|-----|---------|----------|
| `STATE_API_URL` | State API endpoint URL | Yes |
| `AGENT_ID` | Agent identifier (default: `dev_ops_agent`) | Yes |
| `GCP_PROJECT` | Google Cloud project ID | Yes |
| `GEMINI_MODEL` | Model name for AI tasks | Yes |
| `OLLAMA_BASE_URL` | Local Ollama endpoint | Yes (for local reasoning) |
| `GOOGLE_APPLICATION_CREDENTIALS` | GCP service account key | Yes (production) |

---

## Validation & Testing Commands

| Command | What It Validates |
|---------|-------------------|
| `npm run lint` | ESLint code linting |
| `npm test` | **Not defined** — `echo "Error: no test specified" && exit 1` |
| `python -c "from models import *"` | Pydantic model import validation |
| `node dispatch.js` | Start agent loop (manual) |
| `node manage.js status` | Check agent status |
| `node manage.js dispatch <task>` | Queue a task |

**Critical Gap:** Zero automated tests. The agent infrastructure has no test coverage.

---

## Key Business Logic / Pipeline Milestones

1. **Task Queue** — `state-api` receives and stores tasks in Firestore `agent_state` collection
2. **Agent Poll** — `dispatch.js` polls `state-api` for `pending_task` status
3. **Task Execution** — Agent transitions to `working`, executes `gsd headless auto --json`
4. **Event Streaming** — JSONL events from GSD streamed back to `state-api` as `last_event`
5. **Completion** — Agent reports `success` or `failed`, transitions to `idle`
6. **Management** — `manage.js` CLI for status checks and manual task injection

### Critical Business Rules

- Single source of truth: `GAME_PLAN.md` is the boss, `STATE.md` is the memory
- Self-delegation: Agent can assign tasks to itself via `state-api`
- Cloud-native first: Vertex AI for tools, Ollama for reasoning
- Shared DNA: All projects consume assets from central `DNA` project
- Resource Governor: High-accuracy tasks → cloud models; creative tasks → local models; financial data → local-only

### Data Flow

```
manage.js → state-api (task injection)
dispatch.js → state-api (task polling, status updates, event streaming)
state-api → Firestore (persistence)
All projects → state-api (status, events)
```

---

## Migration Debt Watch

| Item | Risk | Recommendation |
|------|------|----------------|
| `state-api` is a stub | No real Firestore integration | Implement full CRUD with Firestore |
| `dispatch.js` has no retry/backoff | Agent dies on transient errors | Add exponential backoff and retry logic |
| `manage.js` is minimal | No task history, no log tailing | Add `manage.js logs --tail`, `manage.js history` |
| No package.json dependencies | Missing `@google-cloud/firestore`, `@google-cloud/functions-framework` | Add real dependencies |
| `ingest_docs.js` is a simulation stub | No actual Vertex AI Search integration | Replace with real API calls |
| `test_gemini.py` uses deprecated model | `gemini-1.0-pro` is retired | Update to `gemini-2.0-flash` |
| No bounded context for agent | `gsd headless auto` reads entire workspace | Task payload should include `workspace` and `files` scope |
| No verification step | Agent claims "done" without proof | Add mandatory verification command + output check |
| `models.py` not imported by any function | Pydantic models exist but aren't used | Wire into `publish_content` and other functions |
| Duplicate `dispatch.js` files | Root, `dev_ops/scripts/`, and legacy `Evolution_Dev/` | Pick one canonical version |