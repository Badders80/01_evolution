# Evolution Stables — Sprint System

> **Sprints are scoped, time-bound work units with a single goal.**
> This doc tracks active/completed sprints. Details live in `sprints/`.
> Daily sessions live in `logs/`.

---

## How Sprints Work

### Sprint Lifecycle

```
Planned → In Progress → Complete → Archived
```

| Status | Emoji | Meaning |
|--------|-------|---------|
| Planned | 🔴 | Goal defined, checklist ready, not started |
| In Progress | 🟡 | Active work happening |
| Complete | ✅ | All checklist items done, definition of done met |
| Archived | ⚪ | Sprint done, details in `sprints/`, summary here |

### Sprint Rules

1. **One active sprint at a time.** Lock scope when starting. No scope creep.
2. **Sprints have a single goal.** If you need two goals, split into two sprints.
3. **Checklist is the contract.** Every item must be ticked. No skipping.
4. **Definition of done is the gate.** All criteria must pass before marking complete.
5. **Daily sessions log to `logs/`.** Sprints span multiple sessions. Each session gets a log entry.
6. **Sprint details live in `sprints/`.** This file only tracks status + summary.

### How to Start a Sprint

1. Read `SPRINTS.md` — see what's active
2. If no active sprint, pick a planned one or plan a new one
3. Write sprint details to `sprints/S{number}-{date}-{name}.md`
4. Update `SPRINTS.md` — mark as 🟡 In Progress
5. Lock scope — no new items added mid-sprint

### How to End a Sprint

1. Verify all checklist items are ticked
2. Verify definition of done criteria are met
3. Mark sprint ✅ Complete in `SPRINTS.md`
4. Write sprint retrospective to `sprints/S{number}-{date}-{name}.md`
5. Archive sprint (move to "Archived Sprints" section)
6. Start next sprint or plan one

---

## Active Sprint

### Sprint 003: Task Master Hub — MVP v1
**Status:** 🟡 In Progress  
**Date:** 2026-05-20  
**Goal:** Establish `01_evolution` as the centralized task management hub for all projects  
**Details:** [`sprints/S003-2026-05-20-taskmaster-hub.md`](sprints/S003-2026-05-20-taskmaster-hub.md)

---

## Planned Sprints

### Sprint 004: Investor Update Editor
**Status:** 🔴 Planned  
**Date:** 2026-05-20  
**Goal:** Build investor update editor with structured content entry → production HTML outputs  
**Details:** [`sprints/S004-2026-05-20-investor-update-editor.md`](sprints/S004-2026-05-20-investor-update-editor.md)

---

## Completed Sprints

### Sprint 002: Horse Registration + Content Upload (V1 Admin Workflow)
**Status:** ✅ Complete  
**Date:** 2026-05-20  
**Goal:** Wire V1 admin workflow — register horses and upload content  
**Summary:** ✅ Complete
- Horse registration form wired to SSOT API with validation
- Content upload flow with drag-drop, file type/size validation
- Horse detail page with image gallery and lightbox
- Error states + success feedback throughout
- 22 pages build with 0 errors
**Details:** [`sprints/S002-2026-05-20-horse-registration.md`](sprints/S002-2026-05-20-horse-registration.md)

### Sprint 001: Design Token System + Admin Primitives
**Status:** ✅ Complete  
**Date:** 2026-05-20  
**Goal:** Tokenize design language + build admin primitives  
**Summary:** ✅ Complete
- Fixed build blocker (`outline-ring/50` error)
- Refactored 6 admin pages to use primitives (owners, trainers, FAQ, assets, horse registration, press)
- All 22 pages build with 0 errors
- Admin primitives now used consistently across all pages
**Details:** [`sprints/S001-2026-05-20-design-tokens.md`](sprints/S001-2026-05-20-design-tokens.md)

---

## Sprint History

| Sprint | Date | Goal | Status | Detail File |
|--------|------|------|--------|-------------|
| 003 | 2026-05-20 | Task Master Hub | 🟡 In Progress | [`sprints/S003-2026-05-20-taskmaster-hub.md`](sprints/S003-2026-05-20-taskmaster-hub.md) |
| 002 | 2026-05-20 | Horse Registration + Content Upload | ✅ Complete | [`sprints/S002-2026-05-20-horse-registration.md`](sprints/S002-2026-05-20-horse-registration.md) |
| 001 | 2026-05-20 | Design Token System + Admin Primitives | ✅ Complete | [`sprints/S001-2026-05-20-design-tokens.md`](sprints/S001-2026-05-20-design-tokens.md) |

---

## Related Documents

- **Daily sessions:** [`logs/`](logs/) — Session-by-session narrative
- **Roadmap:** [`../GAME_PLAN.md`](../GAME_PLAN.md) — 9 checkpoints
- **Diary:** [`PROGRESS.md`](PROGRESS.md) — What's next, architecture status
- **Map:** [`BUILD_SUMMARY.md`](BUILD_SUMMARY.md) — What exists, the rules
