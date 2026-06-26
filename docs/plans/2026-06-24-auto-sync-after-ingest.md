# Plan: Auto-Sync After Email Ingest

**Date:** 2026-06-24
**Status:** Draft — pending review
**Author:** glm-5.2

## Problem

After `batch_ingest.py` processes emails, transcripts are written to `api/email-ingest/output/` but never synced to the two downstream layers:

1. **`_assets/horses/{slug}/transcripts/`** — the canonical media library
2. **`01_evolution/horses/{slug}/transcripts.md`** — the auto-generated knowledge repo index

This requires a manual `cp` + `python3 tools/index_horse.py {slug}` after every batch run. If forgotten, the knowledge repo goes stale and the website/backend can't see new content.

## Goal

After `batch_ingest.py` finishes processing all emails, automatically:
1. Copy any new transcript JSON files from `output/` to `_assets/horses/{slug}/transcripts/`
2. Run `tools/index_horse.py {slug}` for each unique horse that had new content
3. Log what was synced

## Design

### Approach: Post-batch sync function in `batch_ingest.py`

Add a `sync_to_assets()` function called at the end of `main()`, after all emails are processed.

```python
def sync_to_assets(processed_horses: set[str]):
    """Sync new transcripts from output/ to _assets/ and regenerate indexes.
    
    Args:
        processed_horses: Set of horse slugs that had new content in this batch.
    """
    import shutil
    import subprocess
    
    script_dir = os.path.dirname(os.path.abspath(__file__))
    output_dir = os.path.join(script_dir, "output")
    
    # _assets is at workspace root: ../../_assets from api/email-ingest/
    assets_root = os.path.join(script_dir, "..", "..", "..", "_assets")
    # tools/index_horse.py is at ../../tools/ from api/email-ingest/
    tools_dir = os.path.join(script_dir, "..", "..", "tools")
    
    for horse_slug in processed_horses:
        # Normalize slug (lowercase, no spaces)
        horse_slug = horse_slug.lower().replace(" ", "-")
        
        # Target: _assets/horses/{slug}/transcripts/
        target_dir = os.path.join(assets_root, "horses", horse_slug, "transcripts")
        os.makedirs(target_dir, exist_ok=True)
        
        # Copy transcript files for this horse from output/
        # Files are named: transcript_{HorseName}_{date}.json
        safe_prefix = horse_slug.replace("-", "")
        copied = 0
        for f in os.listdir(output_dir):
            if f.startswith("transcript_") and f.endswith(".json"):
                # Match by horse name in filename (case-insensitive)
                if horse_slug.lower() in f.lower():
                    src = os.path.join(output_dir, f)
                    dst = os.path.join(target_dir, f)
                    if not os.path.exists(dst):
                        shutil.copy2(src, dst)
                        logger.info(f"  → Synced: {f} → _assets/horses/{horse_slug}/transcripts/")
                        copied += 1
                    else:
                        logger.info(f"  → Already synced: {f}")
        
        if copied > 0:
            # Regenerate the knowledge repo index
            index_script = os.path.join(tools_dir, "index_horse.py")
            if os.path.exists(index_script):
                result = subprocess.run(
                    ["python3", index_script, horse_slug],
                    capture_output=True, text=True, timeout=30
                )
                if result.returncode == 0:
                    logger.info(f"  → Regenerated transcripts.md for {horse_slug}")
                else:
                    logger.warning(f"  → index_horse.py failed: {result.stderr[:200]}")
            else:
                logger.warning(f"  → index_horse.py not found at {index_script}")
        else:
            logger.info(f"  → No new transcripts to sync for {horse_slug}")
```

### Integration point

In `main()`, after the batch summary, before the final log:

```python
    # Collect unique horse slugs from successful results
    processed_horses = set()
    for raw_email in raw_emails:
        # We need the horse slug, not just the subject
        # Re-parse to get the clean horse name
        try:
            parsed = parse_email(raw_email)
            slug = parsed.horse_name.lower().replace(" ", "-")
            processed_horses.add(slug)
        except Exception:
            pass
    
    # Sync to _assets and regenerate indexes
    if processed_horses:
        logger.info("\n=== SYNCING TO ASSETS ===")
        sync_to_assets(processed_horses)
        logger.info("=== SYNC COMPLETE ===\n")
```

### Edge cases handled

1. **Horse directory doesn't exist in `_assets/`** — `os.makedirs(target_dir, exist_ok=True)` creates it
2. **Transcript already synced** — checks `os.path.exists(dst)` before copying, skips duplicates
3. **`index_horse.py` not found** — logs warning, doesn't crash
4. **`index_horse.py` fails** — logs stderr, continues to next horse
5. **No new transcripts** — skips index regeneration (no point regenerating if nothing changed)
6. **Multiple horses in one batch** — iterates the set of unique horse slugs

### What this does NOT do

- Does not sync race acceptance emails (text-only) — those don't produce transcript files
- Does not upload to GCS or any cloud — purely local file sync
- Does not commit to git — that's a separate step (pre-commit hook handles validation)
- Does not sync video files — those are downloaded to `/tmp/`, transcribed, then deleted. Raw videos live in `_assets/horses/{slug}/videos/` from a separate import process

## Files to modify

| File | Change |
|------|--------|
| `api/email-ingest/batch_ingest.py` | Add `sync_to_assets()` function + call it at end of `main()` |

## Files NOT modified

- `tools/index_horse.py` — no changes needed, called as-is via subprocess
- `parser.py` — no changes needed
- `model_router.py` — no changes needed

## Testing

1. Clear the ledger + NDJSON + `_assets/horses/prudentia/transcripts/` (remove the 2 new files)
2. Run `batch_ingest.py`
3. Verify:
   - Transcript files appear in `_assets/horses/prudentia/transcripts/`
   - `horses/prudentia/transcripts.md` lists all 6 transcripts
   - Log output shows "Synced" and "Regenerated" messages
4. Run again — verify "Already synced" messages (idempotent)

## Risk Assessment

- **Low risk** — only adds a post-processing step, doesn't change existing ingest logic
- **Failure mode** — if sync fails, the ingest itself still succeeded (transcripts are in `output/`)
- **Rollback** — just remove the `sync_to_assets()` call from `main()`

---

## Review by kimi-k2.7-code (2026-06-24)

### CRITICAL (3 issues — must fix before implementation)

1. **Wrong relative path depth** — `../../..` from `api/email-ingest/` goes to repo parent, not repo root. Fix: use `../../_assets` (two levels up, not three).

2. **Path traversal via unsanitized horse_slug** — slug comes from email content, only lowercased/spaces-replaced. A malicious email with `horse_name = "../../evil"` would write outside `_assets/horses/`. Fix: validate slug against `^[a-z0-9_-]+$` regex, reject path separators and `..`.

3. **Fragile filename matching** — `horse_slug.lower() in f.lower()` is a substring match. `horse_slug = "art"` would match `transcript_Arty_*.json`. Cross-contamination risk. Fix: parse the horse name deterministically from the filename using the same `transcript_{HorseName}_{date}.json` pattern.

### WARN (8 issues — should fix)

4. **Idempotency gap** — if `index_horse.py` fails on first run, re-run sees `copied == 0` and never retries the index regeneration. Fix: track index success separately.
5. **Same-name files never overwritten** — `if not os.path.exists(dst)` means corrected transcripts with same filename won't update. Fix: compare checksums/mtime or overwrite.
6. **Subprocess cwd** — `index_horse.py` may expect to run from repo root, but inherits `api/email-ingest/` as cwd. Fix: set `cwd=repo_root` in `subprocess.run`.
7. **Re-parsing all emails** — collecting horse slugs by re-parsing `raw_emails` is wasteful and includes failed ingests. Fix: collect slug from successful results.
8. **Hard-coded 30s timeout** — may be too short. Fix: make configurable.
9. **No concurrency/locking** — overlapping batch runs could race. Fix: add file lock.
10. **Error handling too narrow** — single bad file crashes whole sync. Fix: per-horse try/except.
11. **index_horse.py behavior assumed** — plan assumes it writes `transcripts.md` but doesn't verify. Fix: confirm or add explicit step.

### NIT (4 issues — nice to fix)

12. Unused `safe_prefix` variable
13. Move `import shutil/subprocess` to module top
14. Truncated stderr (200 chars) hides Python tracebacks
15. Prefer importing `index_horse` function over subprocess for testability

### Revised implementation priorities

1. Fix path: `../../_assets` (2 levels, not 3)
2. Validate slug: `re.match(r'^[a-z0-9_-]+$', horse_slug)`
3. Deterministic filename matching: parse `transcript_{name}_{date}.json` pattern
4. Per-horse try/except
5. Set `cwd` for subprocess
6. Collect slugs from successful results only