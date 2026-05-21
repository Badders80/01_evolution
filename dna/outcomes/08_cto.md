# Extraction Report: Evolution_CTO

**Source:** `/home/evo/workspace/projects/Evolution_CTO`
**Date:** 2026-05-19
**Extraction Role:** Lead Cloud Architect — outcome-driven, ignoring current execution methods

---

## Final Artifacts & Deployment Targets

| Artifact | Description | Target |
|----------|-------------|--------|
| Aggregate dashboard data | Task counts per project, health status | Firestore collection `projects` |
| Priority/decision documents | Cross-project direction from CTO | Firestore collection `direction` |
| Learning documents | Per-project patterns and pitfalls | Firestore collection `learnings` |
| Sprint retrospectives | Weekly retro data | Firestore collection `retros` |

---

## Core Tech Stack & Hard Dependencies

| Dependency | Purpose | Notes |
|------------|---------|-------|
| Node.js | Dashboard scripts | `dashboard/scripts/refresh-aggregate.js` |
| JSON files | Data storage | `aggregate.json`, `priorities.json`, `decisions.json` |

**This project is document-based, not code-based.** The "CTO" role is a management layer, not a deployable service.

---

## Environment Variables & Secrets (Keys Only)

None required. This project has no external service dependencies.

---

## Validation & Testing Commands

| Command | What It Validates |
|---------|-------------------|
| None | No code to validate |

---

## Key Business Logic / Pipeline Milestones

1. **Aggregate** — Scan all project `.taskmaster/` directories for task counts and statuses
2. **Prioritize** — CTO sets cross-project priorities in `direction/priorities.json`
3. **Decide** — CTO records pending decisions in `direction/decisions.json`
4. **Learn** — Per-project patterns and pitfalls recorded in `learnings/`
5. **Retro** — Weekly retrospective data captured

### Critical Business Rules

- CTO reads horizontally (initiatives, health, dependencies)
- Project PMs read vertically (tasks, sprints, features)
- Direction flows downward from CTO to projects
- Aggregation flows upward from projects to CTO dashboard

### Data Flow

```
All projects → Evolution_CTO (task counts, statuses, blockers)
Evolution_CTO → All projects (priorities, decisions, bets)
```

---

## Migration Debt Watch

| Item | Risk | Recommendation |
|------|------|----------------|
| JSON file-based storage | No real-time, no query capability | Migrate to Firestore `projects` collection |
| No automation | Manual `refresh-aggregate.js` script | Replace with Firestore triggers |
| No web dashboard | CLI-only management | Build lightweight Next.js status dashboard reading from `state-api` |
| Already partially replaced | `AGENTS.md` + `dispatch.js` + `manage.js` in vertex_workspace | Formalize the replacement and deprecate CTO project |