#!/usr/bin/env python3
"""Merge Evolution_Content ledger into email-ingest local ledger."""

from __future__ import annotations

import argparse
import json
import logging
import os
import re
import shutil
import sqlite3
import sys
from datetime import datetime

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
INGEST_DIR = os.path.normpath(os.path.join(SCRIPT_DIR, ".."))
sys.path.insert(0, INGEST_DIR)

from archive_media import normalize_horse_slug  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

DATA_DIR = os.path.join(INGEST_DIR, "data")
NEW_LEDGER = os.getenv("INGEST_DB_PATH", os.path.join(DATA_DIR, "ledger.sqlite"))
NEW_NDJSON = os.getenv("INGEST_NDJSON_PATH", os.path.join(DATA_DIR, "content-index.ndjson"))
LEGACY_LEDGER = "/home/evo/workspace/projects/Evolution_Content/data/ledger.sqlite"
LEGACY_NDJSON = "/home/evo/workspace/projects/Evolution_Content/catalog/content-index.ndjson"

HORSE_NAME_FIXES = {
    "audio update: prudentia": "Prudentia",
    ": prudentia": "Prudentia",
    "prudentia": "Prudentia",
}

FALSE_POSITIVE_SUBJECTS = [
    re.compile(r"prize funds distribution", re.I),
]


def _normalize_horse_display(name: str) -> str:
    key = name.lower().strip()
    if key in HORSE_NAME_FIXES:
        return HORSE_NAME_FIXES[key]
    if key.startswith("audio update:"):
        return key.split(":", 1)[1].strip().title()
    try:
        slug = normalize_horse_slug(name)
        return slug.replace("-", " ").title()
    except ValueError:
        return name


def _is_false_positive(subject: str, from_address: str) -> bool:
    if "wexfordstables" not in (from_address or "").lower():
        return True
    return any(p.search(subject) for p in FALSE_POSITIVE_SUBJECTS)


def _normalize_extracted(extracted: dict) -> dict:
    if not extracted:
        return extracted
    horse = extracted.get("horse")
    if horse:
        extracted["horse"] = _normalize_horse_display(horse)
    return extracted


def _backup(path: str) -> str:
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    dest = f"{path}.bak.{ts}"
    shutil.copy2(path, dest)
    logger.info("Backup: %s", dest)
    return dest


def _purge_bad_rows(conn: sqlite3.Connection, *, dry_run: bool) -> int:
    rows = conn.execute("SELECT id, subject, from_address FROM emails").fetchall()
    to_delete = [r[0] for r in rows if _is_false_positive(r[1], r[2])]
    if dry_run:
        logger.info("Would delete %d false-positive row(s): %s", len(to_delete), to_delete)
        return len(to_delete)
    for row_id in to_delete:
        conn.execute("DELETE FROM emails WHERE id = ?", (row_id,))
    conn.commit()
    logger.info("Deleted %d false-positive row(s)", len(to_delete))
    return len(to_delete)


def _existing_keys(conn: sqlite3.Connection) -> tuple[set[str], set[tuple[str, str]]]:
    message_ids: set[str] = set()
    subject_dates: set[tuple[str, str]] = set()
    for row in conn.execute("SELECT message_id, subject, date_received FROM emails"):
        if row[0]:
            message_ids.add(row[0])
        if row[1] and row[2]:
            subject_dates.add((row[1], row[2]))
    return message_ids, subject_dates


def merge_legacy(*, dry_run: bool) -> dict:
    if not os.path.exists(LEGACY_LEDGER):
        raise FileNotFoundError(f"Legacy ledger not found: {LEGACY_LEDGER}")

    if not dry_run and os.path.exists(NEW_LEDGER):
        _backup(NEW_LEDGER)
    if not dry_run and os.path.exists(NEW_NDJSON):
        _backup(NEW_NDJSON)

    new_conn = sqlite3.connect(NEW_LEDGER)
    new_conn.row_factory = sqlite3.Row
    legacy_conn = sqlite3.connect(LEGACY_LEDGER)
    legacy_conn.row_factory = sqlite3.Row

    new_conn.execute("""
        CREATE TABLE IF NOT EXISTS emails (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            from_address TEXT NOT NULL,
            subject TEXT NOT NULL,
            date_received DATETIME,
            body_text TEXT,
            body_html TEXT,
            extracted_json TEXT,
            source_type TEXT DEFAULT 'email',
            status TEXT DEFAULT 'unread',
            file_path TEXT,
            message_id TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)

    purged = _purge_bad_rows(new_conn, dry_run=dry_run)
    msg_ids, subj_dates = _existing_keys(new_conn)

    legacy_rows = legacy_conn.execute(
        "SELECT * FROM emails ORDER BY date_received"
    ).fetchall()

    inserted = 0
    skipped = 0
    normalized = 0

    for row in legacy_rows:
        subject = row["subject"] or ""
        from_addr = row["from_address"] or ""
        if _is_false_positive(subject, from_addr):
            skipped += 1
            continue

        message_id = row["message_id"] or ""
        date_received = row["date_received"] or ""

        if message_id and message_id in msg_ids:
            skipped += 1
            continue
        if (subject, date_received) in subj_dates:
            skipped += 1
            continue

        extracted_raw = row["extracted_json"] or "{}"
        try:
            extracted = json.loads(extracted_raw)
        except json.JSONDecodeError:
            extracted = {}
        extracted = _normalize_extracted(extracted)

        if dry_run:
            inserted += 1
            continue

        new_conn.execute(
            """
            INSERT INTO emails (
                from_address, subject, date_received, body_text, body_html,
                extracted_json, source_type, status, file_path, message_id, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                from_addr,
                subject,
                date_received,
                row["body_text"],
                row["body_html"],
                json.dumps(extracted),
                row["source_type"] or "email",
                row["status"] or "unread",
                row["file_path"],
                message_id or None,
                row["created_at"] or datetime.now().isoformat(),
            ),
        )
        inserted += 1
        if message_id:
            msg_ids.add(message_id)
        subj_dates.add((subject, date_received))

    # Normalize horse names on all existing rows
    for row in new_conn.execute("SELECT id, extracted_json FROM emails"):
        try:
            extracted = json.loads(row["extracted_json"] or "{}")
        except json.JSONDecodeError:
            continue
        old_horse = extracted.get("horse", "")
        extracted = _normalize_extracted(extracted)
        if extracted.get("horse") != old_horse:
            normalized += 1
            if not dry_run:
                new_conn.execute(
                    "UPDATE emails SET extracted_json = ? WHERE id = ?",
                    (json.dumps(extracted), row["id"]),
                )

    if not dry_run:
        new_conn.commit()

    total = new_conn.execute("SELECT COUNT(*) FROM emails").fetchone()[0]
    new_conn.close()
    legacy_conn.close()

    if not dry_run:
        rebuild_ndjson(NEW_LEDGER, NEW_NDJSON)

    return {
        "purged": purged,
        "inserted": inserted,
        "skipped": skipped,
        "normalized": normalized,
        "total_rows": total if not dry_run else "dry-run",
    }


def rebuild_ndjson(ledger_path: str, ndjson_path: str) -> int:
    conn = sqlite3.connect(ledger_path)
    conn.row_factory = sqlite3.Row
    rows = conn.execute("SELECT * FROM emails ORDER BY date_received, id").fetchall()
    conn.close()

    os.makedirs(os.path.dirname(ndjson_path), exist_ok=True)
    count = 0
    with open(ndjson_path, "w", encoding="utf-8") as f:
        for row in rows:
            try:
                extracted = json.loads(row["extracted_json"] or "{}")
            except json.JSONDecodeError:
                extracted = {}
            entry = {
                "event": "email_ingested",
                "timestamp": row["created_at"] or datetime.now().isoformat(),
                "email": {
                    "id": row["id"],
                    "from": row["from_address"],
                    "subject": row["subject"],
                    "date": row["date_received"],
                    "extracted": extracted,
                    "status": row["status"],
                    "ingested_by": "merge_legacy_ledger",
                },
            }
            f.write(json.dumps(entry) + "\n")
            count += 1
    logger.info("Rebuilt NDJSON: %s (%d lines)", ndjson_path, count)
    return count


def main() -> int:
    parser = argparse.ArgumentParser(description="Merge Evolution_Content ledger into email-ingest")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    stats = merge_legacy(dry_run=args.dry_run)
    logger.info("Merge stats: %s", stats)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())