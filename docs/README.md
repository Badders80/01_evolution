# Documentation

**Purpose:** Project documentation — progress tracking, build summaries, session logs, sprints, and audits.

---

## Structure

```
docs/
├── SPRINTS.md             ← Sprint registry — active, planned, completed sprints
├── sprints/               ← Sprint detail files
│   └── S001-YYYY-MM-DD-name.md  ← One file per sprint (checklist, scope, DOD)
├── PROGRESS.md            ← The diary — session log, what's next, architecture status
├── BUILD_SUMMARY.md       ← The map — what the project is, what exists, the rules
├── logs/                  ← Daily session notes
│   └── YYYY-MM-DD.md      ← One file per build session
└── audit/                 ← Quality audits
    ├── AUDIT.md           ← Living audit summary
    └── reports/           ← Full audit reports
        └── AUDIT_YYYY-MM-DD.md
```

## The Two Docs

| Doc | Role | Updated |
|-----|------|---------|
| **PROGRESS.md** | The diary — session log, what's next, architecture status | Every session |
| **BUILD_SUMMARY.md** | The map — what the project is, what exists, the rules | Only when landscape shifts |

## Session Logging

**Trigger:** Run `/end` at end of session.

Every session creates a log file in `logs/YYYY-MM-DD.md` and updates PROGRESS.md. BUILD_SUMMARY.md is only updated when new routes, pages, or architecture rules are added.

**Update:** Automatically by `/done` skill

---

## Audits

### Audit Summary (`audit/AUDIT.md`)

Living document with:
- Current assessment scores (infrastructure, code, docs)
- Audit log (one row per audit)
- Open issues

### Audit Reports (`audit/reports/`)

Full audit reports:
- **Format:** `AUDIT_YYYY-MM-DD.md`
- **Content:** Comprehensive review of all systems
- **Frequency:** End-of-day or weekly

---

## Session Workflow

```bash
# Start of session
./.agents/scripts/startup-check.sh

# Shows:
# - Whether today is already logged
# - Yesterday's activity
# - Current progress
# - What's next

# End of session
/done

# Creates:
# - docs/logs/YYYY-MM-DD.md
# - Updates docs/PROGRESS.md session table
```

---

## Related

- **[README.md](../README.md)** — Project overview
- **[GAME_PLAN.md](../GAME_PLAN.md)** — 9 checkpoints
- **[.agents/scripts/](../.agents/scripts/)** — Startup check script
- **[.agents/skills/done/](../.agents/skills/done/)** — /done skill
