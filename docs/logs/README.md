# Session Logs

**Purpose:** Daily build session notes — what got done, what's next.

**One file per day:** `YYYY-MM-DD.md`

**Trigger:** Run `/end` at end of session.

---

## Format

```markdown
# YYYY-MM-DD — {Focus Area}

**Date:** {ISO_DATE}
**Focus:** {main focus — 3-5 words}
**Files Changed:** {count}

**Keywords:** {comma-separated}

## Tasks
- [x] {completed task}
- [ ] {unfinished task}

## Decisions
- {architecture decision}

## Blockers
- {resolved blocker} ✅

## Shipped
{1–2 sentences summary}

## Unfinished
{what carries to next session}

## Narrative
{2–5 sentences}

## Next
{what should happen next session}

## Verification
{last build/test command and result}
```

---

## Doc Structure

| Doc | Role | Updated |
|-----|------|---------|
| `logs/YYYY-MM-DD.md` | Daily session notes | Every session |
| `PROGRESS.md` | The diary — session log, what's next, architecture status | Every session |
| `BUILD_SUMMARY.md` | The map — what the project is, what exists, the rules | Only when landscape shifts |
{next session focus}
```

---

## Workflow

### End of Session

1. Say `/done` or "wrap up"
2. Skill auto-generates log from conversation
3. Writes to `docs/logs/YYYY-MM-DD.md`
4. Updates session table in `docs/PROGRESS.md`

### Start of Next Session

1. Run `./.agents/scripts/startup-check.sh`
2. Shows yesterday's log summary
3. Shows what's next from PROGRESS.md

---

## Files

| File | Purpose |
|------|---------|
| [`2026-05-19.md`](2026-05-19.md) | Setup + Backend Deployment (first session) |

---

## Related

- **[PROGRESS.md](../PROGRESS.md)** — Living summary with session table
- **[AUDIT.md](../audit/AUDIT.md)** — Quality assessments
- **[startup-check.sh](../../.agents/scripts/startup-check.sh)** — Startup verification
