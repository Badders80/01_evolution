#!/usr/bin/env python3
"""One-off CDN recovery: download archived media URLs from NDJSON + ledger."""

from __future__ import annotations

import argparse
import csv
import json
import logging
import os
import sqlite3
import sys
from dataclasses import dataclass
from datetime import date
from typing import Iterable, Optional

import requests

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
INGEST_DIR = os.path.normpath(os.path.join(SCRIPT_DIR, ".."))
sys.path.insert(0, INGEST_DIR)

from archive_media import (  # noqa: E402
    base_archive_dest,
    derive_original_label,
    infer_extension,
    infer_media_kind,
    normalize_horse_slug,
    parse_content_date,
    resolve_archive_dest,
    sha256_file,
    to_relative_asset_path,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

DATA_DIR = os.path.join(INGEST_DIR, "data")
NDJSON_PATH = os.getenv("INGEST_NDJSON_PATH", os.path.join(DATA_DIR, "content-index.ndjson"))
LEDGER_PATH = os.getenv("INGEST_DB_PATH", os.path.join(DATA_DIR, "ledger.sqlite"))
LEGACY_LEDGER_PATH = "/home/evo/workspace/projects/Evolution_Content/data/ledger.sqlite"
MANIFEST_PATH = os.path.join(DATA_DIR, "media-download-manifest.csv")


@dataclass(frozen=True)
class MediaRecord:
    url: str
    horse_name: str
    received_date: date
    subject: str
    source: str


def _parse_ndjson(path: str) -> list[MediaRecord]:
    records: list[MediaRecord] = []
    if not os.path.exists(path):
        logger.warning("NDJSON not found: %s", path)
        return records

    with open(path, encoding="utf-8") as f:
        for line_no, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                entry = json.loads(line)
            except json.JSONDecodeError as exc:
                logger.warning("Skipping NDJSON line %d: %s", line_no, exc)
                continue

            email = entry.get("email", {})
            extracted = email.get("extracted", {})
            horse_name = extracted.get("horse") or ""
            received_date = parse_content_date(email.get("date", ""))
            if received_date is None:
                received_date = parse_content_date(extracted.get("race_date", ""))
            subject = email.get("subject", "")

            for url in extracted.get("video_urls") or []:
                if url and _is_media_url(url):
                    records.append(
                        MediaRecord(
                            url=url,
                            horse_name=horse_name,
                            received_date=received_date or date.today(),
                            subject=subject,
                            source="ndjson",
                        )
                    )
    return records


def _parse_ledger(path: str, source_label: str) -> list[MediaRecord]:
    records: list[MediaRecord] = []
    if not os.path.exists(path):
        logger.warning("Ledger not found: %s", path)
        return records

    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    try:
        rows = conn.execute(
            "SELECT subject, date_received, extracted_json FROM emails WHERE extracted_json IS NOT NULL"
        ).fetchall()
    except sqlite3.Error as exc:
        logger.warning("Could not read ledger %s: %s", path, exc)
        conn.close()
        return records

    for row in rows:
        try:
            extracted = json.loads(row["extracted_json"] or "{}")
        except json.JSONDecodeError:
            continue

        horse_name = extracted.get("horse") or ""
        received_date = parse_content_date(row["date_received"] or "")
        if received_date is None:
            received_date = parse_content_date(extracted.get("race_date", ""))
        subject = row["subject"] or ""

        for url in extracted.get("video_urls") or []:
            if url and _is_media_url(url):
                records.append(
                    MediaRecord(
                        url=url,
                        horse_name=horse_name,
                        received_date=received_date or date.today(),
                        subject=subject,
                        source=source_label,
                    )
                )
    conn.close()
    return records


def collect_records(include_legacy: bool) -> list[MediaRecord]:
    records: list[MediaRecord] = []
    records.extend(_parse_ndjson(NDJSON_PATH))
    records.extend(_parse_ledger(LEDGER_PATH, "ledger"))
    if include_legacy:
        records.extend(_parse_ledger(LEGACY_LEDGER_PATH, "legacy_ledger"))
    return records


def dedupe_by_url(records: Iterable[MediaRecord]) -> list[MediaRecord]:
    """Keep earliest received_date per URL."""
    best: dict[str, MediaRecord] = {}
    for rec in records:
        existing = best.get(rec.url)
        if existing is None or rec.received_date < existing.received_date:
            best[rec.url] = rec
    return sorted(best.values(), key=lambda r: (r.received_date, r.url))


def filter_records(
    records: list[MediaRecord],
    *,
    horse: Optional[str],
    from_date: Optional[date],
    to_date: Optional[date],
) -> list[MediaRecord]:
    filtered: list[MediaRecord] = []
    for rec in records:
        try:
            slug = normalize_horse_slug(rec.horse_name)
        except ValueError:
            logger.warning("Skipping record with invalid horse name: %r", rec.horse_name)
            continue

        if horse and slug != normalize_horse_slug(horse):
            continue
        if from_date and rec.received_date < from_date:
            continue
        if to_date and rec.received_date > to_date:
            continue
        filtered.append(rec)
    return filtered


def _is_media_url(url: str) -> bool:
    """Only Prism CDN media files — skip banners, portal pages, images."""
    lower = url.lower()
    if "/assets/" in lower or "/portal/" in lower:
        return False
    if not any(ext in lower for ext in (".mp4", ".mp3", ".m4a", ".mov", ".webm")):
        return False
    return "prism.horse/media/" in lower or lower.endswith((".mp4", ".mp3", ".m4a", ".mov", ".webm"))


MIN_MEDIA_BYTES = 500_000  # reject banner/HTML stubs (<500KB)


def download_url(url: str, dest_path: str, timeout: int = 120) -> int:
    os.makedirs(os.path.dirname(dest_path), exist_ok=True)
    resp = requests.get(url, stream=True, timeout=timeout)
    resp.raise_for_status()
    with open(dest_path, "wb") as f:
        for chunk in resp.iter_content(chunk_size=8192):
            if chunk:
                f.write(chunk)
    nbytes = os.path.getsize(dest_path)
    if nbytes < MIN_MEDIA_BYTES and not url.lower().endswith(".mp3"):
        os.unlink(dest_path)
        raise ValueError(f"Download too small ({nbytes} bytes) — likely corrupt or non-media URL")
    return nbytes


def process_record(rec: MediaRecord, *, dry_run: bool, skip_existing: bool) -> dict:
    horse_slug = normalize_horse_slug(rec.horse_name)
    media_kind = infer_media_kind(rec.url)
    original_label = derive_original_label(
        source_url=rec.url,
        media_kind=media_kind,
        subject=rec.subject,
    )
    ext = infer_extension(rec.url)
    canonical_dest = base_archive_dest(horse_slug, rec.received_date, original_label, ext)
    dest_path = canonical_dest
    rel_path = to_relative_asset_path(dest_path)

    row = {
        "url": rec.url,
        "horse_slug": horse_slug,
        "received_date": rec.received_date.isoformat(),
        "dest_path": rel_path,
        "status": "pending",
        "bytes": 0,
        "sha256": "",
        "subject": rec.subject,
        "source": rec.source,
    }

    if skip_existing and os.path.exists(canonical_dest) and os.path.getsize(canonical_dest) > 0:
        row["status"] = "skipped_existing"
        row["bytes"] = os.path.getsize(canonical_dest)
        row["sha256"] = sha256_file(canonical_dest)
        logger.info("Skip existing: %s", rel_path)
        return row

    dest_path = resolve_archive_dest(horse_slug, rec.received_date, original_label, ext)
    rel_path = to_relative_asset_path(dest_path)
    row["dest_path"] = rel_path

    if dry_run:
        row["status"] = "dry_run"
        logger.info("DRY RUN: %s → %s", rec.url[:80], rel_path)
        return row

    try:
        nbytes = download_url(rec.url, dest_path)
        row["status"] = "downloaded"
        row["bytes"] = nbytes
        row["sha256"] = sha256_file(dest_path)
        logger.info("Downloaded %d bytes → %s", nbytes, rel_path)
    except Exception as exc:
        row["status"] = f"error:{exc}"
        logger.error("Failed %s: %s", rec.url, exc)

    return row


def write_manifest(rows: list[dict], path: str) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    fieldnames = ["url", "horse_slug", "received_date", "dest_path", "status", "bytes", "sha256"]
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow(row)
    logger.info("Wrote manifest: %s (%d rows)", path, len(rows))


def main() -> int:
    parser = argparse.ArgumentParser(description="Download archived media from NDJSON + ledger URLs")
    parser.add_argument("--dry-run", action="store_true", help="List URLs and target paths only")
    parser.add_argument("--include-legacy-ledger", action="store_true", help="Include Evolution_Content ledger")
    parser.add_argument("--from", dest="from_date", metavar="YYYY-MM-DD", help="Filter from received_date")
    parser.add_argument("--to", dest="to_date", metavar="YYYY-MM-DD", help="Filter to received_date")
    parser.add_argument("--horse", help="Filter by horse slug (e.g. prudentia)")
    parser.add_argument("--skip-existing", action="store_true", default=True, help="Skip if dest exists (default)")
    parser.add_argument("--no-skip-existing", dest="skip_existing", action="store_false")
    parser.add_argument("--manifest", default=MANIFEST_PATH, help="Manifest CSV output path")
    args = parser.parse_args()

    from_date = date.fromisoformat(args.from_date) if args.from_date else None
    to_date = date.fromisoformat(args.to_date) if args.to_date else None

    records = collect_records(args.include_legacy_ledger)
    records = dedupe_by_url(records)
    records = filter_records(records, horse=args.horse, from_date=from_date, to_date=to_date)

    logger.info("Processing %d unique URL(s)", len(records))
    rows = [process_record(rec, dry_run=args.dry_run, skip_existing=args.skip_existing) for rec in records]
    write_manifest(rows, args.manifest)

    downloaded = sum(1 for r in rows if r["status"] == "downloaded")
    skipped = sum(1 for r in rows if r["status"] == "skipped_existing")
    errors = sum(1 for r in rows if r["status"].startswith("error"))
    logger.info("Done: %d downloaded, %d skipped, %d errors", downloaded, skipped, errors)
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())