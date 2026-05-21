# /done — Session Capture

**Trigger:** User says "done", "wrap up", "end session", "log session"

When invoked, auto-generate and **write immediately**. Edits optional.

---

## Step 0: Detect sprint mode

Check `docs/PROGRESS.md` for active sprint context.

**If sprint context found** → SPRINT MODE (use Sprint Capture format)
**If not found** → STANDARD MODE (use Standard Capture format)

---

## Sprint Capture (with /sprint)

### Format:

```markdown
# {ISO_DATE} — Sprint {N}: {TITLE}

**Project:** Evolution Stables  
**Sprint:** {sprint number + title}  
**Sprint goal:** {goal from sprint start}  
**vs Goal:** {SHIPPED / PARTIAL / MISSED}

**Keywords:** {comma-separated, flat}

## Tasks
- [x] {shipped task}
- [ ] {unfinished task}

## Decisions
- {decision}

## Blockers
- {new blocker}
- {resolved blocker} ✅

## Shipped
{1–2 sentences}

## Unfinished
{what's left for next session}

## Narrative
{2–5 sentences}

## Next
{what should happen next session}
```

### After writing:
- Write to `docs/logs/YYYY-MM-DD.md`
- Update session table in `docs/PROGRESS.md`
- If sprint state changed, note in PROGRESS.md

---

## Standard Capture (no /sprint)

### Format:

```markdown
# {ISO_DATE} — {TITLE}

**Date:** {ISO_DATE}  
**Focus:** {main focus area}  
**Duration:** {estimated time}  
**Files Changed:** {count}

**Keywords:** {comma-separated, flat}

## Tasks
- [x] {shipped task}
- [ ] {unfinished task}

## Decisions
- {decision}

## Blockers
- {new blocker}
- {resolved blocker} ✅

## Shipped
{1–2 sentences}

## Unfinished
{what was started but not completed}

## Narrative
{2–5 sentences}

## Next
{what should happen next session}
```

### After writing:
- Write to `docs/logs/YYYY-MM-DD.md`
- Add row to session table in `docs/PROGRESS.md`

---

## Rules (both modes)

- **Write immediately.** Never gate on confirmation.
- After writing, show what was saved: "Written. Edits?"
- If user wants edits, edit in place.
- Use UTC ISO timestamps
- If no real work happened, keep it to 2 sentences, no task list
- If conversation compacted, note it in narrative
- One log file per day (append if already exists)

---

## File Locations

- Session logs: `docs/logs/YYYY-MM-DD.md`
- Progress summary: `docs/PROGRESS.md`
- Skill definition: `.agents/skills/done/SKILL.md`

---

## Example Usage

**User:** "done"

**Agent:**
```
Wrapping up? Let me log this session.

1. What was the main focus? (e.g., "Backend deployment")
2. What got done? (I can suggest from our conversation)
3. What's next?

[User answers]

✅ Session logged to docs/logs/2026-05-19.md
📊 Updated docs/PROGRESS.md

Next session: Build admin pages (owners, trainers)
```

---

## Notes

- If user doesn't answer questions, use conversation context to infer
- Always create dated log file (one per day)
- If log already exists for today, append instead of overwrite
- Update PROGRESS.md session table automatically
