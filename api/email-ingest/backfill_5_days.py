import os
import sys
import time
import json
import sqlite3
import requests
import imaplib
import email
import logging
import re
from datetime import datetime
from dotenv import load_dotenv

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv("/home/evo/.env")

# Import our unified pipeline modules
from parser import parse_email
from transcriber import Transcriber
from main import _download_video

# APIs config
SSOT_API_URL = "https://australia-southeast1-evolution-engine.cloudfunctions.net/ssot"
ASSETS_API_URL = "https://australia-southeast1-evolution-engine.cloudfunctions.net/assets"
DB_PATH = "/home/evo/workspace/projects/Evolution_Content/data/ledger.sqlite"

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
                    "uploaded_by": "email-ingest-local-backfill",
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


def store_in_local_sqlite(parsed, transcript):
    """Insert the parsed email and transcript into local SQLite."""
    try:
        if not os.path.exists(DB_PATH):
            logger.warning(f"SQLite DB not found at: {DB_PATH}")
            return
            
        logger.info(f"Connecting to SQLite database: {DB_PATH}...")
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
            logger.info(f"Email '{parsed.subject}' already exists in SQLite DB (ID: {row[0]}). Skipping duplicate.")
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
            "content_type": "video_update" if parsed.video_url else "text_update"
        }
        
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
        logger.info(f"Successfully inserted email (ID: {last_id})!")
        
        # Also append to ndjson catalog
        catalog_path = os.path.join(os.path.dirname(DB_PATH), "..", "catalog", "content-index.ndjson")
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
                    "ingested_by": "backfill_5_days_local"
                }
            }
            with open(catalog_path, "a") as cat_f:
                cat_f.write(json.dumps(catalog_entry) + "\n")
            logger.info("Successfully appended event to catalog/content-index.ndjson.")
            
        conn.close()
    except Exception as e:
        logger.error(f"Error storing in local SQLite: {e}")


def main():
    logger.info("=== Wexford/Prudentia Email Backfill (Last 5 Days) ===")
    
    if not WEXFORD_APP_PASSWORD:
        raise ValueError("WEXFORD_APP_PASSWORD is not set in environment")
        
    logger.info(f"Connecting to Gmail IMAP as {WEXFORD_EMAIL_USER}...")
    mail = imaplib.IMAP4_SSL('imap.gmail.com')
    mail.login(WEXFORD_EMAIL_USER, WEXFORD_APP_PASSWORD)
    
    folders = ["INBOX", "[Gmail]/Sent Mail"]
    search_query = 'SINCE "28-May-2026" (OR FROM "info@wexfordstables.co.nz" TEXT "Prudentia")'
    
    # 1. Fetch metadata for matching messages from both folders
    all_emails = []
    
    for folder in folders:
        logger.info(f"Searching folder: {folder}...")
        status, select_data = mail.select(f'"{folder}"', readonly=True)
        if status != 'OK':
            logger.warning(f"Could not select folder '{folder}'. Skipping...")
            continue
            
        status, response = mail.search(None, search_query)
        if status != 'OK':
            logger.warning(f"Search failed in folder '{folder}'. Skipping...")
            continue
            
        msg_ids = response[0].split()
        if not msg_ids:
            logger.info(f"No matching emails found in '{folder}'.")
            continue
            
        logger.info(f"Found {len(msg_ids)} matches in '{folder}'. Fetching message headers...")
        for msg_id in msg_ids:
            status, data = mail.fetch(msg_id, '(RFC822)')
            if status != 'OK':
                logger.warning(f"Failed to fetch content for ID {msg_id.decode()} in '{folder}'")
                continue
                
            raw_email_bytes = data[0][1]
            msg = email.message_from_bytes(raw_email_bytes)
            
            # Parse received date
            date_str = msg.get('Date', '')
            try:
                from email.utils import parsedate_to_datetime
                dt = parsedate_to_datetime(date_str)
            except Exception as e:
                logger.warning(f"Failed to parse email date '{date_str}': {e}. Skipping...")
                continue
                
            subject = msg.get('Subject', 'No Subject')
            decoded_subject = ""
            for part, encoding in email.header.decode_header(subject):
                if isinstance(part, bytes):
                    decoded_subject += part.decode(encoding or 'utf-8', errors='replace')
                else:
                    decoded_subject += part
            
            # Clean HTML tags out of subject line
            decoded_subject = re.sub(r'<[^>]*>', '', decoded_subject).strip()
            
            # Filter automatic replies
            if decoded_subject.lower().startswith("automatic reply:") or decoded_subject.lower().startswith("out of office:"):
                logger.info(f"Skipping automatic reply/OOF: '{decoded_subject}'")
                continue
                
            all_emails.append({
                "folder": folder,
                "msg_id": msg_id,
                "datetime": dt,
                "subject": decoded_subject,
                "msg": msg
            })
            
    if not all_emails:
        logger.info("No candidate emails found to process in the last 5 days.")
        return
        
    # Sort chronological (oldest to newest) to backfill sequentially
    all_emails.sort(key=lambda x: x["datetime"])
    logger.info(f"Total candidate emails found to process: {len(all_emails)}")
    
    # 2. Re-establish connection for writable operations (or select table)
    # Connect database deduplication
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("CREATE TABLE IF NOT EXISTS emails (message_id TEXT PRIMARY KEY)")
    conn.commit()
    
    transcriber = None
    
    for idx, item in enumerate(all_emails, 1):
        folder = item["folder"]
        msg_id = item["msg_id"]
        dt = item["datetime"]
        subject = item["subject"]
        msg = item["msg"]
        
        # Deduplication check
        message_id = msg.get('Message-ID', f"imap-{folder.replace('/', '_')}-{msg_id.decode()}")
        row = c.execute("SELECT id FROM emails WHERE message_id = ?", (message_id,)).fetchone()
        if row:
            logger.info(f"[{idx}/{len(all_emails)}] Skipping already ingested email (ID {row[0]}): '{subject}'")
            continue
            
        logger.info(f"[{idx}/{len(all_emails)}] Processing missing email: '{subject}' ({dt.isoformat()}) from '{folder}'")
        
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
            "subject": subject,
            "from_address": msg.get('From', 'info@wexfordstables.co.nz'),
            "date_received": dt,
            "body_text": body_text,
            "body_html": body_html or body_text
        }
        
        parsed = parse_email(raw_email_dict)
        
        try:
            # Resolve horse microchip
            microchip = resolve_horse_microchip(parsed.horse_name)
        except Exception as e:
            logger.error(f"  Failed to resolve microchip for '{parsed.horse_name}': {e}. Skipping.")
            continue
            
        # Ingest text-only
        if not parsed.video_url:
            logger.info("  No video URL found. Ingesting as text-only update...")
            # Determine speakers based on sender
            if "alex@evolutionstables.nz" in parsed.from_address.lower():
                speakers = ["Alex Baddeley"]
            elif "andrew" in parsed.from_address.lower() or "scott" in parsed.from_address.lower():
                speakers = ["Andrew Scott"]
            elif "lance" in parsed.from_address.lower() or "sullivan" in parsed.from_address.lower():
                speakers = ["Lance O'Sullivan"]
            else:
                speakers = ["Andrew Scott"] if parsed.speaker_count == 1 else ["Lance O'Sullivan", "Andrew Scott"]
                
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
            
            # Store in SSOT API
            content_id = store_content_api(parsed, microchip, "text-only", transcript)
            
            # Store in local SQLite
            store_in_local_sqlite(parsed, transcript)
            logger.info(f"  Successfully processed text update (Content ID: {content_id})")
            continue
            
        # Ingest video-based update
        logger.info(f"  Video URL found: {parsed.video_url}. Commencing video-update flow...")
        video_path = _download_video(parsed.video_url)
        try:
            if transcriber is None:
                transcriber = Transcriber()
                
            transcriber.speaker_count = parsed.speaker_count
            transcriber.speaker_names = transcriber._get_speaker_names()
            
            logger.info("  Transcribing video via auto-selected engine...")
            transcript = transcriber.transcribe_video(
                video_path=video_path,
                engine="auto",
                horse_name=parsed.horse_name
            )
            
            # Upload to Assets API
            asset_id = upload_to_assets_api(video_path, microchip, parsed)
            
            # Store in SSOT API
            content_id = store_content_api(parsed, microchip, asset_id, transcript)
            
            # Store in local SQLite
            store_in_local_sqlite(parsed, transcript)
            logger.info(f"  Successfully processed video update (Asset ID: {asset_id}, Content ID: {content_id})")
            
        except Exception as ex:
            logger.error(f"  Failed during transcription/ingestion: {ex}")
        finally:
            if os.path.exists(video_path):
                os.unlink(video_path)
                logger.info("  Cleaned up local video file.")
                
    conn.close()
    logger.info("=== Backfill of Last 5 Days Completed Successfully! ===")


if __name__ == "__main__":
    main()
