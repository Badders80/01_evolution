#!/usr/bin/env python3
"""Export transcript text from ledger to JSON files in output/ and _assets/."""

from __future__ import annotations

import json
import logging
import os
import re
import shutil
import sqlite3
import sys

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
INGEST_DIR = os.path.normpath(os.path.join(SCRIPT_DIR, ".."))
sys.path.insert(0, INGEST_DIR)

from archive_media import normalize_horse_slug  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

DATA_DIR = os.path.join(INGEST_DIR, "data")
LEDGER = os.getenv("INGEST_DB_PATH", os.path.join(DATA_DIR, "ledger.sqlite"))
OUTPUT_DIR = os.path.join(INGEST_DIR, "output")
ASSETS_TRANSCRIPTS = os.path.normpath(
    os.path.join(INGEST_DIR, "..", "..", "..", "_assets", "horses", "prudentia", "transcripts")
)

MIN_TRANSCRIPT_LEN = 80
HTML_MARKERS = ("<html", "<!doctype", "body {", "@media")


def _looks_like_html(text: str) -> bool:
    lower = text[:2000].lower()
    return any(m in lower for m in HTML_MARKERS)


def _filename(horse: str, content_date: str) -> str:
    safe = re.sub(r"[^\w\-]", "_", horse)
    return f"transcript_{safe}_{content_date}.json"


def main() -> int:
    conn = sqlite3.connect(LEDGER)
    conn.row_factory = sqlite3.Row
    rows = conn.execute("SELECT id, subject, extracted_json FROM emails ORDER BY id").fetchall()
    conn.close()

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    os.makedirs(ASSETS_TRANSCRIPTS, exist_ok=True)

    exported = 0
    skipped = 0

    for row in rows:
        try:
            extracted = json.loads(row["extracted_json"] or "{}")
        except json.JSONDecodeError:
            skipped += 1
            continue

        transcript = (extracted.get("transcript") or "").strip()
        if len(transcript) < MIN_TRANSCRIPT_LEN or _looks_like_html(transcript):
            skipped += 1
            continue

        horse = extracted.get("horse") or "Prudentia"
        try:
            normalize_horse_slug(horse)
        except ValueError:
            horse = "Prudentia"

        content_date = extracted.get("race_date") or ""
        if not content_date or len(content_date) < 10:
            skipped += 1
            continue

        payload = {
            "full_text": transcript,
            "segments": [],
            "source": "ledger_export",
            "model": "legacy",
            "speakers": ["Andrew Scott"],
            "subject": row["subject"],
            "ledger_id": row["id"],
        }
        fname = _filename(horse, content_date[:10])
        out_path = os.path.join(OUTPUT_DIR, fname)
        asset_path = os.path.join(ASSETS_TRANSCRIPTS, fname)

        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2)
        shutil.copy2(out_path, asset_path)
        logger.info("Exported: %s", fname)
        exported += 1

    logger.info("Done: %d exported, %d skipped", exported, skipped)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())