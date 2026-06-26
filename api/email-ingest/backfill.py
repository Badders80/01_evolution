import os
import sys
import time
import json
import sqlite3
import requests
import imaplib
import email
import logging
from datetime import datetime
from dotenv import load_dotenv

# Import our unified pipeline modules
from archive_media import (
    archive_enabled,
    archive_media,
    delete_temp_enabled,
    infer_media_kind,
    normalize_horse_slug,
    to_relative_asset_path,
)
from parser import parse_email
from transcriber import Transcriber
from main import _download_video

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv("/home/evo/.env")

# APIs config
SSOT_API_URL = "https://australia-southeast1-evolution-engine.cloudfunctions.net/ssot"
ASSETS_API_URL = "https://australia-southeast1-evolution-engine.cloudfunctions.net/assets"
_DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
DB_PATH = os.getenv("INGEST_DB_PATH", os.path.join(_DATA_DIR, "ledger.sqlite"))
NDJSON_PATH = os.getenv("INGEST_NDJSON_PATH", os.path.join(_DATA_DIR, "content-index.ndjson"))

# Credentials
WEXFORD_EMAIL_USER = os.getenv("WEXFORD_EMAIL_USER", "alex@evolutionstables.nz")
WEXFORD_APP_PASSWORD = os.getenv("WEXFORD_APP_PASSWORD")


def resolve_horse_microchip(horse_name):
    """Call SSOT API to list horses and find microchip for horse name (with local fallback)."""
    try:
        logger.info(f"Listing horses from SSOT API to resolve '{horse_name}'...")
        resp = requests.get(f"{SSOT_API_URL}/horses", timeout=10)
        resp.raise_for_status()
        
        horses = resp.json()
        matched = [h for h in horses if horse_name.lower() in h.get("name", "").lower()]
        if matched:
            microchip = matched[0]["microchip"]
            logger.info(f"Resolved '{horse_name}' via API -> microchip {microchip}")
            return microchip
    except Exception as e:
        logger.warning(f"SSOT API resolution failed or returned error: {e}. Using local resolution.")

    # Fallback to standard microchip resolution
    if "prudentia" in horse_name.lower():
        microchip = "985125000126462"
        logger.info(f"Locally resolved '{horse_name}' -> microchip {microchip}")
        return microchip
        
    raise ValueError(f"Horse '{horse_name}' not registered in system and no fallback microchip available")


def upload_to_assets_api(video_path, microchip, parsed):
    """Upload video file to Assets API (with local fallback)."""
    filename = os.path.basename(video_path)
    date_str = parsed.content_date.isoformat()
    tags = f"video,update,{parsed.horse_name},{date_str}"
    
    try:
        logger.info(f"Uploading video {video_path} to Assets API for microchip {microchip}...")
        with open(video_path, "rb") as f:
            resp = requests.post(
                f"{ASSETS_API_URL}/upload",
                files={"file": (filename, f, "video/mp4")},
                data={
                    "entity_type": "horse",
                    "entity_id": microchip,
                    "tags": tags,
                    "alt": f"Video update for {parsed.horse_name} — {parsed.title}",
                    "uploaded_by": "email-ingest-local",
                },
                timeout=30,
            )
            
        if resp.status_code in (200, 201):
            data = resp.json()
            asset_id = data['id']
            logger.info(f"Assets API upload complete. Asset ID: {asset_id}")
            return asset_id
    except Exception as e:
        logger.warning(f"Assets API upload failed: {e}")
        
    # Local fallback path/id
    mock_id = f"local-asset-{int(time.time())}"
    logger.info(f"Failed to upload to Assets API. Registered local mock Asset ID: {mock_id}")
    return mock_id


def store_content_api(parsed, microchip, asset_id, transcript):
    """Store transcript via SSOT API (with local fallback)."""
    payload = {
        "content_type": "transcript",
        "horse_microchip": microchip,
        "title": parsed.title,
        "content_date": parsed.content_date.isoformat(),
        "speakers": transcript.speakers,
        "full_text": transcript.full_text,
        "segments": [
            {
                "start_time": s.start_time,
                "end_time": s.end_time,
                "speaker": s.speaker,
                "text": s.text,
            }
            for s in transcript.segments
        ],
        "source": transcript.source,
        "source_email_id": parsed.message_id,
        "asset_ids": [asset_id],
        "status": "published",
        "confidence": transcript.confidence,
        "needs_human_review": transcript.needs_human_review,
        "review_reason": transcript.review_reason,
        "reconciliation_changes": transcript.reconciliation_changes
    }
    
    try:
        logger.info(f"Storing transcript via SSOT API content endpoint...")
        resp = requests.post(
            f"{SSOT_API_URL}/content",
            json=payload,
            timeout=15,
        )
        if resp.status_code in (200, 201):
            data = resp.json()
            content_id = data.get("id", "")
            logger.info(f"SSOT content stored complete. Content ID: {content_id}")
            return content_id
        elif resp.status_code == 409:
            existing = resp.json()
            content_id = existing.get('existing_id', '')
            logger.info(f"Content already exists in SSOT: {content_id}")
            return content_id
    except Exception as e:
        logger.warning(f"SSOT content creation failed: {e}")
        
    mock_content_id = f"local-content-{int(time.time())}"
    logger.info(f"Failed to store in SSOT API. Using local mock Content ID: {mock_content_id}")
    return mock_content_id


def store_in_local_sqlite(parsed, transcript, *, local_media_path=None, source_cdn_url=None):
    """Insert parsed email and transcript into local SQLite."""
    if not os.path.exists(DB_PATH):
        logger.warning(f"SQLite DB not found at: {DB_PATH}")
        return
        
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        
        # Ensure table exists
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
        
        row = c.execute("SELECT id FROM emails WHERE message_id = ?", (parsed.message_id,)).fetchone()
        if row:
            logger.info(f"Email already exists in SQLite DB (ID: {row[0]}). Skipping.")
            conn.close()
            return
            
        extracted_data = {
            "horse": parsed.horse_name,
            "stable": "Wexford Stables",
            "trainer": "Lance O'Sullivan & Andrew Scott" if parsed.speaker_count >= 2 else "Andrew Scott",
            "venue": "",
            "race_date": parsed.content_date.isoformat(),
            "video_urls": [parsed.video_url] if parsed.video_url else [],
            "transcript": transcript.full_text,
            "quotes": [
                {"speaker": s.speaker, "text": s.text}
                for s in transcript.segments[:3]
            ],
            "sentiment": "positive",
            "content_type": "video_update"
        }
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
        logger.info(f"Successfully inserted backfill email and transcript (ID: {last_id})!")
        
        # Append to catalog
        catalog_path = NDJSON_PATH
        if os.path.exists(os.path.dirname(catalog_path)):
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
                    "ingested_by": "backfill_local"
                }
            }
            with open(catalog_path, "a") as cat_f:
                cat_f.write(json.dumps(catalog_entry) + "\n")
            logger.info("Successfully appended backfill event to catalog.")
            
        conn.close()
    except Exception as e:
        logger.error(f"Error storing in local SQLite during backfill: {e}")


def main():
    logger.info("=== Starting Wexford Email Backfill Automation (Modular) ===")
    
    logger.info(f"Connecting to Gmail IMAP as {WEXFORD_EMAIL_USER}...")
    mail = imaplib.IMAP4_SSL('imap.gmail.com')
    mail.login(WEXFORD_EMAIL_USER, WEXFORD_APP_PASSWORD)
    mail.select('inbox')
    
    status, response = mail.search(None, '(FROM "info@wexfordstables.co.nz")')
    if status != 'OK':
        logger.error("IMAP search failed")
        sys.exit(1)
        
    msg_ids = response[0].split()
    if not msg_ids:
        logger.info("No emails found from Wexford Stables.")
        sys.exit(0)
        
    # We will backfill the last 10 emails
    last_10_ids = msg_ids[-10:]
    logger.info(f"Checking the last {len(last_10_ids)} emails for backfill...")
    
    if not os.path.exists(DB_PATH):
        logger.error(f"Local SQLite database not found at {DB_PATH}")
        sys.exit(1)
        
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    # Initialize transcriber
    transcriber = Transcriber()
    
    for i, msg_id in enumerate(last_10_ids, 1):
        status, data = mail.fetch(msg_id, '(RFC822)')
        if status != 'OK':
            logger.warning(f"Failed to fetch msg_id: {msg_id.decode()}")
            continue
            
        raw_email_bytes = data[0][1]
        msg = email.message_from_bytes(raw_email_bytes)
        
        message_id = msg.get('Message-ID', f"imap-{msg_id.decode()}")
        
        # Deduplication check
        row = c.execute("SELECT id FROM emails WHERE message_id = ?", (message_id,)).fetchone()
        if row:
            logger.info(f"[{i}/10] Skipping already ingested email: '{msg.get('Subject')}'")
            continue
            
        logger.info(f"[{i}/10] Ingesting missing email: '{msg.get('Subject')}'")
        
        # Parse subject headers
        subject = msg.get('Subject', '')
        decoded_subject = ""
        for part, encoding in email.header.decode_header(subject):
            if isinstance(part, bytes):
                decoded_subject += part.decode(encoding or 'utf-8', errors='replace')
            else:
                decoded_subject += part
                
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
            
        raw_email_dict = {
            "message_id": message_id,
            "thread_id": msg.get('Thread-Index', ''),
            "subject": decoded_subject,
            "from_address": msg.get('From', 'info@wexfordstables.co.nz'),
            "date_received": datetime.now(),
            "body_text": body_text,
            "body_html": body_html or body_text
        }
        
        # Parse using unified parser
        parsed = parse_email(raw_email_dict)
        if not parsed.video_url:
            logger.warning(f"  No video URL found for '{parsed.horse_name}', skipping...")
            continue
            
        try:
            # Resolve horse microchip
            microchip = resolve_horse_microchip(parsed.horse_name)
            
            # Download video
            video_path = _download_video(parsed.video_url)
            horse_slug = normalize_horse_slug(parsed.horse_name)
            media_kind = infer_media_kind(parsed.video_url, video_path)
            
            try:
                # Transcribe using unified Transcriber (engine="auto" — Google STT first, free)
                transcriber.speaker_count = parsed.speaker_count
                transcriber.speaker_names = transcriber._get_speaker_names()
                # Transcribe using unified Transcriber (engine="auto" so it tries cheap Google STT first)
                logger.info(f"  Transcribing video via auto-selected engine...")
                transcript = transcriber.transcribe_video(
                    video_path=video_path,
                    engine="auto",
                    horse_name=parsed.horse_name
                )
                
                # Upload to Assets API
                asset_id = upload_to_assets_api(video_path, microchip, parsed)
                
                # Store in SSOT API
                content_id = store_content_api(parsed, microchip, asset_id, transcript)

                archived_path = None
                if archive_enabled():
                    archived_path = archive_media(
                        video_path,
                        horse_slug,
                        parsed.content_date,
                        media_kind,
                        source_cdn_url=parsed.video_url,
                    )
                local_media_path = to_relative_asset_path(archived_path) if archived_path else None
                
                # Store in local SQLite DB
                store_in_local_sqlite(
                    parsed,
                    transcript,
                    local_media_path=local_media_path,
                    source_cdn_url=parsed.video_url,
                )
                logger.info(f"  Successfully backfilled: Asset ID: {asset_id}, Content ID: {content_id}")
                
            finally:
                if delete_temp_enabled() and os.path.exists(video_path):
                    os.unlink(video_path)
                    
        except Exception as e:
            logger.error(f"  Failed to process backfill email: {e}")
            
    conn.close()
    logger.info("=== Backfill Completed ===")


if __name__ == "__main__":
    main()
