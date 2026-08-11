"""
Batch Email Ingest — fetch and process trainer emails by subject pattern.

Usage:
    python3 api/email-ingest/batch_ingest.py --source wexford
    python3 api/email-ingest/batch_ingest.py --source stephen-gray

Processes all matching emails (video updates + race acceptances) in chronological order.
Handles both video-update emails (with transcription) and text-only emails (race acceptances).
"""

import argparse
import os
import sys
import re
import json
import time
import shutil
import subprocess
import imaplib
import email
import email.header
import logging
import sqlite3
from datetime import datetime
from email.utils import parsedate_to_datetime
from dotenv import load_dotenv

# Add parent dir to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from archive_media import (
    archive_enabled,
    archive_from_parsed,
    archive_images_from_parsed,
    delete_temp_enabled,
    infer_media_kind,
    normalize_horse_slug,
    parse_transcript_filename,
    save_transcript_json,
    to_relative_asset_path,
)
from horse_registry import INGEST_SOURCES, resolve_horse_entry, resolve_horse_microchip
from mistable import extract_report_url
from parser import parse_email, get_speaker_names
from transcriber import Transcriber
from main import _download_video

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv("/home/evo/.env")

# Local-first data paths
_DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
DB_PATH = os.getenv("INGEST_DB_PATH", os.path.join(_DATA_DIR, "ledger.sqlite"))
NDJSON_PATH = os.getenv("INGEST_NDJSON_PATH", os.path.join(_DATA_DIR, "content-index.ndjson"))

# Credentials
WEXFORD_EMAIL_USER = os.getenv("WEXFORD_EMAIL_USER", "alex@evolutionstables.nz")
WEXFORD_APP_PASSWORD = os.getenv("WEXFORD_APP_PASSWORD")

# SSOT API
SSOT_API_URL = "https://australia-southeast1-evolution-engine.cloudfunctions.net/ssot"
ASSETS_API_URL = "https://australia-southeast1-evolution-engine.cloudfunctions.net/assets"


def fetch_matching_emails(
    subject_patterns,
    *,
    imap_query=None,
    date_start=None,
    date_end=None,
):
    """Fetch all emails matching any of the given subject patterns via IMAP.
    
    Args:
        subject_patterns: List of regex patterns to match against subject.
        imap_query: Optional IMAP search expression override.
        date_start: Optional datetime — only include emails after this (inclusive).
        date_end: Optional datetime — only include emails before this (exclusive).
    
    Returns:
        List of raw_email dicts sorted oldest-first.
    """
    if not WEXFORD_APP_PASSWORD:
        raise ValueError("WEXFORD_APP_PASSWORD is not set in environment")
    
    logger.info(f"Connecting to Gmail IMAP as {WEXFORD_EMAIL_USER}...")
    mail = imaplib.IMAP4_SSL('imap.gmail.com')
    mail.login(WEXFORD_EMAIL_USER, WEXFORD_APP_PASSWORD)
    
    all_emails = []
    
    mail.select("INBOX", readonly=True)
    search_query = imap_query or '(OR FROM "info@wexfordstables.co.nz" TEXT "Prudentia")'
    status, response = mail.search(None, search_query)
    
    if status != 'OK':
        raise RuntimeError("IMAP search failed")
    
    msg_ids = response[0].split()
    logger.info(f"Found {len(msg_ids)} total matching emails in INBOX")
    
    # Fetch all of them (we'll filter by subject pattern)
    for msg_id in msg_ids:
        status, data = mail.fetch(msg_id, '(RFC822)')
        if status != 'OK':
            continue
        
        raw_email_bytes = data[0][1]
        msg = email.message_from_bytes(raw_email_bytes)
        
        # Decode subject
        subject = msg.get('Subject', 'No Subject')
        decoded_subject = ""
        for part, encoding in email.header.decode_header(subject):
            if isinstance(part, bytes):
                decoded_subject += part.decode(encoding or 'utf-8', errors='replace')
            else:
                decoded_subject += part
        decoded_subject = re.sub(r'<[^>]*>', '', decoded_subject).strip()
        
        # Check if subject matches any of our patterns
        matched = False
        for pattern in subject_patterns:
            if re.search(pattern, decoded_subject, re.IGNORECASE):
                matched = True
                break
        
        if not matched:
            continue
        
        # Parse date
        date_str = msg.get('Date', '')
        try:
            dt = parsedate_to_datetime(date_str)
        except Exception:
            dt = datetime.now()
        
        # Date range filter
        if date_start and dt < date_start:
            continue
        if date_end and dt >= date_end:
            continue
        
        # Parse body
        body_text = ""
        body_html = ""
        if msg.is_multipart():
            for part in msg.walk():
                ctype = part.get_content_type()
                cdisp = str(part.get('Content-Disposition'))
                if ctype == 'text/plain' and 'attachment' not in cdisp:
                    body_text = part.get_payload(decode=True).decode('utf-8', errors='replace')
                elif ctype == 'text/html' and 'attachment' not in cdisp:
                    body_html = part.get_payload(decode=True).decode('utf-8', errors='replace')
        else:
            body_text = msg.get_payload(decode=True).decode('utf-8', errors='replace')
        
        message_id = msg.get('Message-ID', f"imap-{msg_id.decode()}")
        
        all_emails.append({
            "message_id": message_id,
            "thread_id": msg.get('Thread-Index', ''),
            "subject": decoded_subject,
            "from_address": msg.get('From', 'info@wexfordstables.co.nz'),
            "date_received": dt,
            "body_text": body_text,
            "body_html": body_html or body_text,
            "_msg_id": msg_id.decode(),
        })
    
    mail.logout()
    
    # Sort oldest first (process in chronological order)
    all_emails.sort(key=lambda x: x["date_received"])
    
    logger.info(f"Found {len(all_emails)} emails matching our subject patterns")
    for e in all_emails:
        logger.info(f"  [{e['date_received']}] {e['subject']}")
    
    return all_emails


def store_text_only(parsed, microchip):
    """Store a text-only email (race acceptance, no video)."""
    speakers = get_speaker_names(
        parsed.speaker_count,
        horse_name=parsed.horse_name,
        from_address=parsed.from_address,
    )
    if "alex@evolutionstables.nz" in parsed.from_address.lower():
        speakers = ["Alex Baddeley"]
    
    class TextTranscript:
        def __init__(self, text, speakers):
            self.full_text = text
            self.speakers = speakers
            self.segments = []
            self.source = "email"
            self.confidence = 1.0
            self.needs_human_review = False
            self.review_reason = ""
            self.reconciliation_changes = []
    
    transcript = TextTranscript(parsed.body_text, speakers)
    
    # Store in local SQLite
    store_in_local_sqlite(parsed, transcript)
    
    content_id = f"local-content-{int(time.time())}"
    logger.info(f"  → Text-only stored. Content ID: {content_id}")
    return content_id


def store_video_update(parsed, microchip):
    """Download video, transcribe, and store a video update email."""
    logger.info(f"  → Video URL: {parsed.video_url}")
    
    # Download video
    video_path = _download_video(parsed.video_url)
    horse_slug = normalize_horse_slug(parsed.horse_name)
    media_kind = infer_media_kind(parsed.video_url, video_path)
    
    try:
        # Transcribe
        speaker_names = get_speaker_names(
            parsed.speaker_count,
            horse_name=parsed.horse_name,
            from_address=parsed.from_address,
        )
        transcriber = Transcriber(
            speaker_count=parsed.speaker_count,
            speaker_names=speaker_names,
        )
        stt_engine = os.getenv("INGEST_STT_ENGINE", "aistudio")
        transcript = transcriber.transcribe_video(
            video_path=video_path,
            engine=stt_engine,
            horse_name=parsed.horse_name,
        )

        archived_path = None
        if archive_enabled():
            archived_path = archive_from_parsed(video_path, horse_slug, parsed)
        local_media_path = to_relative_asset_path(archived_path) if archived_path else None
        
        # Store in local SQLite
        store_in_local_sqlite(
            parsed,
            transcript,
            local_media_path=local_media_path,
            source_cdn_url=parsed.video_url,
        )
        
        script_dir = os.path.dirname(os.path.abspath(__file__))
        output_dir = os.path.join(script_dir, "output")
        output_path = save_transcript_json(
            transcript,
            parsed,
            output_dir=output_dir,
            source_path=video_path,
        )
        logger.info(f"  → Transcript saved: {output_path}")
        logger.info(f"  → Full text preview: {transcript.full_text[:200]}...")
        
        return output_path
    finally:
        if delete_temp_enabled() and os.path.exists(video_path):
            os.unlink(video_path)
            logger.info("  → Cleaned up local video file.")


def _normalize_slug(name: str) -> str:
    """Normalize a horse name to a filesystem-safe slug."""
    return normalize_horse_slug(name)


def _parse_transcript_filename(filename: str) -> tuple[str, str] | None:
    """Parse transcript filename → (horse_slug, received_date). Supports legacy names."""
    parsed = parse_transcript_filename(filename)
    if parsed is None:
        return None
    horse_slug, date_str, _original = parsed
    return horse_slug, date_str


def sync_to_assets(processed_horses: dict[str, list[str]]):
    """Sync new transcripts from output/ to _assets/ and regenerate indexes.

    Args:
        processed_horses: Dict mapping horse_slug -> list of transcript filenames
                          that were created in this batch (successful ingests only).
    """
    script_dir = os.path.dirname(os.path.abspath(__file__))
    output_dir = os.path.join(script_dir, "output")

    # _assets is at workspace root: ../../../_assets from api/email-ingest/
    # api/email-ingest/ → api/ → 01_evolution/ → workspace root
    assets_root = os.path.normpath(os.path.join(script_dir, "..", "..", "..", "_assets"))
    # repo root (01_evolution/) is ../../ from api/email-ingest/
    repo_root = os.path.normpath(os.path.join(script_dir, "..", ".."))
    index_script = os.path.join(repo_root, "tools", "index_horse.py")

    if not os.path.isdir(assets_root):
        logger.warning(f"  → _assets directory not found at {assets_root}, skipping sync")
        return

    sync_failures = []

    for horse_slug, transcript_files in processed_horses.items():
        try:
            # Defensive: re-validate slug inside sync_to_assets too
            horse_slug = _normalize_slug(horse_slug)

            # Target: _assets/horses/{slug}/transcripts/
            target_dir = os.path.join(assets_root, "horses", horse_slug, "transcripts")
            os.makedirs(target_dir, exist_ok=True)

            copied = 0
            for filename in transcript_files:
                src = os.path.join(output_dir, filename)
                dst = os.path.join(target_dir, filename)
                if not os.path.exists(src):
                    logger.warning(f"  → Source not found: {filename}")
                    continue
                # Always copy (overwrite) — transcripts may be corrected on re-ingest
                shutil.copy2(src, dst)
                logger.info(f"  → Synced: {filename} → _assets/horses/{horse_slug}/transcripts/")
                copied += 1

            # Regenerate index if we copied new files OR if index is stale
            # (only when there are actual transcript files in the target dir)
            existing_files = [
                f for f in os.listdir(target_dir)
                if f.endswith(".json") and parse_transcript_filename(f) is not None
            ]
            if copied > 0 or (existing_files and os.path.exists(index_script)):
                if os.path.exists(index_script):
                    result = subprocess.run(
                        [sys.executable, index_script, horse_slug],
                        capture_output=True, text=True, timeout=60,
                        cwd=repo_root,
                    )
                    if result.returncode == 0:
                        logger.info(f"  → Regenerated transcripts.md for {horse_slug}")
                    else:
                        logger.warning(f"  → index_horse.py failed for {horse_slug}: {result.stderr[:500]}")
                        sync_failures.append(horse_slug)
                else:
                    logger.warning(f"  → index_horse.py not found at {index_script}")
                    sync_failures.append(horse_slug)

        except Exception as e:
            logger.error(f"  → Sync failed for {horse_slug}: {e}")
            sync_failures.append(horse_slug)

    if sync_failures:
        logger.warning(f"  → Sync failures: {sync_failures}")
    else:
        logger.info("  → All horses synced successfully.")


def is_already_in_ledger(parsed) -> bool:
    """Return True if this email is already ingested (skip re-transcribe)."""
    if not os.path.exists(DB_PATH):
        return False
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    row = c.execute("SELECT id FROM emails WHERE message_id = ?", (parsed.message_id,)).fetchone()
    if row:
        conn.close()
        return True
    # Flexible date match — legacy rows may use Z suffix vs +00:00
    date_str = parsed.date_received.isoformat()
    row = c.execute(
        "SELECT id FROM emails WHERE subject = ? AND (date_received = ? OR date_received = ?)",
        (parsed.subject, date_str, date_str.replace("+00:00", "Z")),
    ).fetchone()
    conn.close()
    return row is not None


def store_in_local_sqlite(parsed, transcript, *, local_media_path=None, source_cdn_url=None):
    """Insert the parsed email and transcript into the local SQLite database."""
    try:
        os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        
        c.execute("""
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
        
        # Dedup check — primary: message_id, secondary: subject + date_received
        row = c.execute("SELECT id FROM emails WHERE message_id = ?", (parsed.message_id,)).fetchone()
        if row:
            logger.info(f"  → Already in DB (ID: {row[0]}). Skipping duplicate.")
            conn.close()
            return
        row = c.execute(
            "SELECT id FROM emails WHERE subject = ? AND date_received = ?",
            (parsed.subject, parsed.date_received.isoformat())
        ).fetchone()
        if row:
            logger.info(f"  → Already in DB (ID: {row[0]}, same subject+date). Skipping duplicate.")
            conn.close()
            return
        
        horse_entry = resolve_horse_entry(parsed.horse_name)
        report_url = extract_report_url(parsed.body_text)
        extracted_data = {
            "horse": horse_entry.display_name,
            "horse_slug": horse_entry.slug,
            "stable": horse_entry.stable,
            "trainer": horse_entry.trainer,
            "venue": "",
            "race_date": parsed.content_date.isoformat(),
            "video_urls": [parsed.video_url] if parsed.video_url else [],
            "transcript": transcript.full_text,
            "content_type": "video_update" if parsed.video_url else "race_acceptance",
        }
        if report_url:
            extracted_data["mistable_report_url"] = report_url
        if local_media_path:
            extracted_data["local_media_path"] = local_media_path
        if source_cdn_url:
            extracted_data["source_cdn_url"] = source_cdn_url
        
        c.execute("""
            INSERT INTO emails (from_address, subject, date_received, body_text, body_html, extracted_json, status, message_id)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            parsed.from_address,
            parsed.subject,
            parsed.date_received.isoformat(),
            transcript.full_text,
            parsed.body_text,
            json.dumps(extracted_data),
            "unread",
            parsed.message_id
        ))
        
        conn.commit()
        last_id = c.lastrowid
        logger.info(f"  → Stored in SQLite (ID: {last_id})")
        
        # Append to NDJSON catalog
        os.makedirs(os.path.dirname(NDJSON_PATH), exist_ok=True)
        catalog_entry = {
            "event": "email_ingested",
            "timestamp": datetime.now().isoformat(),
            "email": {
                "id": last_id,
                "from": parsed.from_address,
                "subject": parsed.subject,
                "date": parsed.date_received.isoformat(),
                "extracted": extracted_data,
                "status": "unread",
                "ingested_by": "batch_ingest"
            }
        }
        with open(NDJSON_PATH, "a") as cat_f:
            cat_f.write(json.dumps(catalog_entry) + "\n")
        logger.info(f"  → Appended to catalog: {NDJSON_PATH}")
        
        conn.close()
    except Exception as e:
        logger.error(f"  → SQLite error: {e}")


def main():
    parser = argparse.ArgumentParser(description="Batch email ingest")
    parser.add_argument(
        "--source",
        choices=sorted(INGEST_SOURCES),
        default=os.getenv("INGEST_SOURCE", "wexford"),
        help="Trainer/source profile to ingest",
    )
    args = parser.parse_args()
    source_cfg = INGEST_SOURCES[args.source]

    logger.info("=== Batch Email Ingest (%s) ===", source_cfg.name)

    subject_patterns = source_cfg.subject_patterns

    from datetime import timezone
    default_end = "2026-07-09" if args.source == "stephen-gray" else "2026-06-27"
    backfill_start = os.getenv("INGEST_BACKFILL_FROM", "2026-02-01")
    backfill_end = os.getenv("INGEST_BACKFILL_TO", default_end)
    y, m, d = map(int, backfill_start.split("-"))
    date_start = datetime(y, m, d, 0, 0, 0, tzinfo=timezone.utc)
    y2, m2, d2 = map(int, backfill_end.split("-"))
    date_end = datetime(y2, m2, d2, 0, 0, 0, tzinfo=timezone.utc)
    logger.info("Date window: %s → %s (UTC)", backfill_start, backfill_end)
    
    # Fetch all matching emails
    raw_emails = fetch_matching_emails(
        subject_patterns,
        imap_query=source_cfg.imap_query,
        date_start=date_start,
        date_end=date_end,
    )
    
    if not raw_emails:
        logger.error("No matching emails found! Check subject patterns.")
        sys.exit(1)
    
    logger.info(f"\nProcessing {len(raw_emails)} emails (oldest first)...\n")
    
    results = []
    
    for i, raw_email in enumerate(raw_emails, 1):
        subject = raw_email["subject"]
        logger.info(f"--- Email {i}/{len(raw_emails)}: {subject} ---")
        logger.info(f"  Date: {raw_email['date_received']}")
        
        try:
            # Parse email
            parsed = parse_email(raw_email)
            logger.info(f"  Horse: {parsed.horse_name}, Date: {parsed.content_date}, Video: {'yes' if parsed.video_url else 'no'}")

            image_paths = archive_images_from_parsed(
                parsed,
                body_html=raw_email.get("body_html", ""),
            )
            if image_paths:
                logger.info("  → Archived %d image(s)", len(image_paths))
            
            skip_existing = os.getenv("INGEST_SKIP_EXISTING", "true").lower() == "true"
            if skip_existing and is_already_in_ledger(parsed):
                logger.info("  → Already in ledger — skipping (INGEST_SKIP_EXISTING=true)")
                results.append({"subject": subject, "status": "skipped_existing"})
                continue

            # Resolve horse
            microchip = resolve_horse_microchip(parsed.horse_name)
            logger.info(f"  Microchip: {microchip}")
            
            # Process based on type
            if parsed.video_url:
                result = store_video_update(parsed, microchip)
                results.append({"subject": subject, "status": "video_transcribed", "result": result})
            else:
                result = store_text_only(parsed, microchip)
                results.append({"subject": subject, "status": "text_only", "result": result})
            
            logger.info(f"  ✅ SUCCESS\n")
            
        except Exception as e:
            logger.error(f"  ❌ FAILED: {e}\n")
            results.append({"subject": subject, "status": "failed", "error": str(e)})
    
    # Summary
    logger.info("\n=== BATCH SUMMARY ===")
    for r in results:
        status_icon = "✅" if r["status"] != "failed" else "❌"
        logger.info(f"  {status_icon} {r['subject']} → {r['status']}")
    
    success_count = sum(1 for r in results if r["status"] != "failed")
    logger.info(f"\n{success_count}/{len(results)} emails processed successfully.")

    # Collect successful horse slugs and their transcript filenames for sync
    # Uses _parse_transcript_filename() for deterministic matching (not substring)
    processed_horses: dict[str, set[str]] = {}
    output_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "output")
    if os.path.isdir(output_dir):
            for filename in os.listdir(output_dir):
            if not filename.endswith(".json"):
                continue
            parsed_fn = _parse_transcript_filename(filename)
            if parsed_fn is None:
                continue
            horse_slug, _date = parsed_fn
            # Only include if this horse had a successful ingest in this batch
            # Check by matching the slug against successful results
            for i, raw_email in enumerate(raw_emails):
                if i < len(results) and results[i]["status"] != "failed":
                    try:
                        parsed_email = parse_email(raw_email)
                        email_slug = _normalize_slug(parsed_email.horse_name)
                        if email_slug == horse_slug:
                            if horse_slug not in processed_horses:
                                processed_horses[horse_slug] = set()
                            processed_horses[horse_slug].add(filename)
                            break
                    except Exception as e:
                        logger.warning(f"  → Could not parse email {i} for slug matching: {e}")

    # Convert sets to sorted lists for sync
    processed_horses_lists = {k: sorted(v) for k, v in processed_horses.items()}

    # Sync to _assets and regenerate indexes
    if processed_horses_lists:
        logger.info("\n=== SYNCING TO ASSETS ===")
        sync_to_assets(processed_horses_lists)
        logger.info("=== SYNC COMPLETE ===")

    logger.info("\n=== BATCH COMPLETE ===")


if __name__ == "__main__":
    main()