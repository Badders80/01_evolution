# Sprint 003: Task Master Hub — MVP v1

> **Sprint detail file.** Lives in `docs/sprints/`.
> **Linked from:** `docs/SPRINTS.md`
> **Session logs:** `docs/logs/YYYY-MM-DD.md`

---

## Sprint 003: Task Master Hub — MVP v1

**Status:** 🟡 In Progress
**Created:** 2026-05-20
**Goal:** Install a minimal Task Master in `01_evolution` that tracks tasks across projects. Human selects tasks, creates sprint markdown manually. No dispatch, no automation.

---

## Scope

### In Scope
- Create `01_evolution/.taskmaster/` directory
- Write `tasks.json` with minimal schema (id, project, title, description, status, priority, dependencies)
- Write `config.json`
- Add `just` commands: `task-list`, `task-next`, `task-show`, `task-start`, `task-done`
- Create 2 sample tasks to prove it works
- Test: select task → create sprint markdown → mark done

### Out of Scope
- executor field
- Dispatch to subagents or OpenFang
- Automatic sprint creation
- 18-task seed graph
- Spawn template updates
- Archive system (add later when tasks accumulate)

---

## Checklist

### Phase 1: Scaffold (5 items)
- [x] 1. Create `01_evolution/.taskmaster/` directory
- [x] 2. Write `tasks.json` with minimal schema (see Schema below)
- [x] 3. Write `config.json` (empty or minimal)
- [x] 4. Verify JSON parses cleanly
- [x] 5. Add `.taskmaster/` to `.gitignore`

### Phase 2: Justfile Commands (5 items)
- [x] 6. Add `just task-list` — shows pending + in-progress tasks
- [x] 7. Add `just task-next` — shows task with no pending dependencies
- [x] 8. Add `just task-show <id>` — shows single task details
- [x] 9. Add `just task-start <id>` — marks task `in-progress`
- [x] 10. Add `just task-done <id>` — marks task `done`

### Phase 3: Test Flow (4 items)
- [x] 11. Create Task 1: "Write Horse Detail Page" (project: 02_website, no deps)
- [x] 12. Create Task 2: "Add Auth Guard" (project: 02_website, deps: [1])
- [x] 13. Run `just task-next` — should return Task 1
- [x] 14. Run `just task-start 1` then `just task-done 1` then `just task-next` — should return Task 2

---

## Definition of Done

1. `just task-list` runs and shows tasks
2. `just task-next` returns the correct next task
3. `just task-start` and `just task-done` update status correctly
4. `just task-show` displays full task details
5. Two sample tasks exist and dependency chain works

---

## Sessions Log

| Date | Focus | Log Link |
|------|-------|----------|
| 2026-05-20 | Sprint planning + MVP v1 design | `logs/2026-05-20-taskmaster.md` |
| TBD | Sprint execution | `logs/YYYY-MM-DD.md` |

---

## Decisions

1. **Task Master tracks tasks only.** No dispatch. No executor. You select a task, create a sprint markdown, and execute manually.
2. **Minimal schema.** `id`, `project`, `title`, `description`, `status`, `priority`, `dependencies`. Nothing else.
3. **Sprints are manual.** You run `just sprint-start <name> --tasks=1,2` and it generates a markdown file. You work from that file.
4. **No archive for now.** Add when task count grows. v1 is about proving the flow.

---

## Schema

```json
{
  "version": "1.0.0",
  "tasks": [
    {
      "id": 1,
      "project": "02_website",
      "title": "Write Horse Detail Page",
      "description": "Build /admin/horses/[microchip] with image gallery",
      "status": "pending",
      "priority": "high",
      "dependencies": []
    },
    {
      "id": 2,
      "project": "02_website",
      "title": "Add Auth Guard",
      "description": "Uncomment guard in admin/layout.tsx",
      "status": "pending",
      "priority": "medium",
      "dependencies": [1]
    }
  ]
}
```

---

## Verification

```bash
cd /home/evo/evo_01/01_evolution

# Test task list
just task-list

# Test next task
just task-next

# Test status change
just task-start 1
just task-done 1
just task-next

# Test show
just task-show 1
```

---

## Fixes Applied Post-Review

| # | Issue | Fix |
|---|-------|-----|
| 1 | `.taskmaster/` not in `.gitignore` | Added to `.gitignore` |
| 2 | `sprint-start` arg format mismatch | Justfile now passes `--tasks={{tasks}}` matching Python script |
| 3 | Sprint title mismatch | Aligned SPRINTS.md and sprint file to "Task Master Hub — MVP v1" |
| 4 | Only 2 sample tasks | Deferred to next sprint — seed 18-task graph |

## Deferred to Next Sprint

1. **Create `02_website/Justfile`** — dev/build/check + task delegation to 01
2. **02_website docs cleanup** — Remove local PROGRESS.md, logs/, audit/; centralize in 01
3. **Seed 18-task graph** — Real work items from PROGRESS.md and GAME_PLAN.md

## Blockers

*(To be filled during sprint)*

---

## Retrospective

*(To be filled when sprint is marked Complete)*
