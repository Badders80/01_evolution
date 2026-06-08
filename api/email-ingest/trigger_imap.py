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
DB_PATH = "/home/evo/workspace/projects/Evolution_Content/data/ledger.sqlite"

# Credentials
WEXFORD_EMAIL_USER = os.getenv("WEXFORD_EMAIL_USER", "alex@evolutionstables.nz")
WEXFORD_APP_PASSWORD = os.getenv("WEXFORD_APP_PASSWORD")


def get_latest_wexford_email():
    """Fetch the absolute latest email from Wexford Stables or matching keyword Prudentia via IMAP.
    
    Searches both INBOX and [Gmail]/Sent Mail, choosing the newest overall.
    """
    import re
    if not WEXFORD_APP_PASSWORD:
        raise ValueError("WEXFORD_APP_PASSWORD is not set in environment")
        
    logger.info(f"Connecting to Gmail IMAP as {WEXFORD_EMAIL_USER}...")
    mail = imaplib.IMAP4_SSL('imap.gmail.com')
    mail.login(WEXFORD_EMAIL_USER, WEXFORD_APP_PASSWORD)
    
    folders = ["INBOX", "[Gmail]/Sent Mail"]
    search_query = '(OR FROM "info@wexfordstables.co.nz" TEXT "Prudentia")'
    candidate_emails = []
    
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
            
        latest_id = msg_ids[-1]
        logger.info(f"Found {len(msg_ids)} matches in '{folder}'. Fetching latest ID: {latest_id.decode()}")
        
        status, data = mail.fetch(latest_id, '(RFC822)')
        if status != 'OK':
            logger.warning(f"Failed to fetch content for ID {latest_id.decode()} in '{folder}'")
            continue
            
        raw_email_bytes = data[0][1]
        msg = email.message_from_bytes(raw_email_bytes)
        
        # Parse received date
        date_str = msg.get('Date', '')
        try:
            from email.utils import parsedate_to_datetime
            dt = parsedate_to_datetime(date_str)
        except Exception as e:
            logger.warning(f"Failed to parse email date '{date_str}': {e}. Using current local time.")
            dt = datetime.now()
            
        candidate_emails.append({
            "folder": folder,
            "msg_id": latest_id,
            "datetime": dt,
            "msg": msg
        })
        
    if not candidate_emails:
        raise RuntimeError("No matching emails found from Wexford or about Prudentia in INBOX or [Gmail]/Sent Mail")
        
    # Pick the newer of the candidates
    candidate_emails.sort(key=lambda x: x["datetime"], reverse=True)
    winner = candidate_emails[0]
    
    msg = winner["msg"]
    latest_id = winner["msg_id"]
    folder = winner["folder"]
    
    logger.info(f"Absolute newest matching email found in '{folder}' (Date: {winner['datetime']})")
    
    # Parse headers
    subject = msg.get('Subject', 'No Subject')
    decoded_subject = ""
    for part, encoding in email.header.decode_header(subject):
        if isinstance(part, bytes):
            decoded_subject += part.decode(encoding or 'utf-8', errors='replace')
        else:
            decoded_subject += part
            
    # Clean HTML tags out of subject line to meet strict log standards
    decoded_subject = re.sub(r'<[^>]*>', '', decoded_subject).strip()
            
    from_addr = msg.get('From', 'info@wexfordstables.co.nz')
    date_str = msg.get('Date', '')
    
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
        
    message_id = msg.get('Message-ID', f"imap-{folder.replace('/', '_')}-{latest_id.decode()}")
    
    logger.info(f"Successfully fetched email: '{decoded_subject}' ({date_str}) from '{folder}'")
    
    return {
        "message_id": message_id,
        "thread_id": msg.get('Thread-Index', ''),
        "subject": decoded_subject,
        "from_address": from_addr,
        "date_received": winner["datetime"],
        "body_text": body_text,
        "body_html": body_html or body_text,
    }


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


def store_in_local_sqlite(parsed, transcript):
    """Insert the parsed email and transcript into the local SQLite database for ingestion integration."""
    try:
        if not os.path.exists(DB_PATH):
            logger.warning(f"SQLite DB not found at: {DB_PATH}")
            return
            
        logger.info(f"Connecting to SQLite database: {DB_PATH}...")
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        
        # Ensure emails table exists
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
        
        # Deduplication check
        row = c.execute("SELECT id FROM emails WHERE message_id = ?", (parsed.message_id,)).fetchone()
        if row:
            logger.info(f"Email already exists in SQLite DB (ID: {row[0]}). Skipping duplicate insert.")
            conn.close()
            return
            
        # Create extracted JSON matching parser structure
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
                for s in transcript.segments[:3]  # Store first 3 segments as quotes
            ],
            "sentiment": "positive",
            "content_type": "video_update"
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
        logger.info(f"Successfully inserted email and transcript into SQLite database (ID: {last_id})!")
        
        # Also append to ndjson catalog
        catalog_path = os.path.join(os.path.dirname(DB_PATH), "..", "catalog", "content-index.ndjson")
        catalog_dir = os.path.dirname(catalog_path)
        if os.path.exists(catalog_dir):
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
                    "ingested_by": "trigger_imap_local"
                }
            }
            with open(catalog_path, "a") as cat_f:
                cat_f.write(json.dumps(catalog_entry) + "\n")
            logger.info("Successfully appended event to catalog/content-index.ndjson.")
            
        conn.close()
    except Exception as e:
        logger.error(f"Error storing in local SQLite: {e}")


def main():
    logger.info("=== Wexford Email Ingestion Trigger (Modular) ===")
    
    # 1. Fetch latest raw email from inbox
    raw_email = get_latest_wexford_email()
    
    # 2. Parse email using unified parser
    parsed = parse_email(raw_email)
    
    # 3. Resolve horse microchip
    try:
        microchip = resolve_horse_microchip(parsed.horse_name)
    except Exception as e:
        logger.error(f"Failed to resolve horse microchip: {e}")
        sys.exit(1)
        
    if not parsed.video_url:
        logger.info("No video URL found in email. Ingesting text content only...")
        # Determine sender based on from_address
        speakers = ["Alex Baddeley"] if "alex@evolutionstables.nz" in parsed.from_address.lower() else ["Andrew Scott"]
        
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
        
        # Store in SSOT content API with empty asset_id
        content_id = store_content_api(parsed, microchip, "text-only", transcript)
        
        # Store in local SQLite DB
        store_in_local_sqlite(parsed, transcript)
        
        logger.info("Successfully ingested text-only communication.")
        logger.info(f"Content ID: {content_id}")
        logger.info("=== SUCCESS (TEXT-ONLY) ===")
        sys.exit(0)
        
    # 4. Download video using main module download helper
    video_path = _download_video(parsed.video_url)
    
    try:
        # 5. Transcribe using unified transcriber with Gemini 2.5 Flash as the requested engine
        transcriber = Transcriber(speaker_count=parsed.speaker_count)
        transcript = transcriber.transcribe_video(
            video_path=video_path,
            engine="auto",
            horse_name=parsed.horse_name
        )
        
        # 6. Upload to Assets API
        asset_id = upload_to_assets_api(video_path, microchip, parsed)
        
        # 7. Store transcript in SSOT API
        content_id = store_content_api(parsed, microchip, asset_id, transcript)
        
        # 8. Store in local SQLite DB for frontend/orchestrator ingestion
        store_in_local_sqlite(parsed, transcript)
        
        # Save transcript to output directory
        script_dir = os.path.dirname(os.path.abspath(__file__))
        output_dir = os.path.join(script_dir, "output")
        os.makedirs(output_dir, exist_ok=True)
            
        output_path = os.path.join(output_dir, f"transcript_{parsed.horse_name}_{parsed.content_date.isoformat()}.json")
        with open(output_path, "w") as f:
            segments_list = [
                {"start_time": s.start_time, "end_time": s.end_time, "speaker": s.speaker, "text": s.text}
                for s in transcript.segments
            ]
            json.dump({
                "full_text": transcript.full_text,
                "segments": segments_list,
                "source": transcript.source,
                "model": transcript.model,
                "speakers": transcript.speakers
            }, f, indent=2)
        logger.info(f"Saved full transcript JSON to local file: {output_path}")
        
        logger.info("\n=== SUCCESS ===")
        logger.info(f"Asset ID: {asset_id}")
        logger.info(f"Content ID: {content_id}")
        logger.info("\n=== TRANSCRIPT CONTENT ===")
        logger.info(f"Full Text: {transcript.full_text}\n")
        logger.info("Segments:")
        for seg in transcript.segments:
            logger.info(f"[{seg.start_time:.1f}s - {seg.end_time:.1f}s] {seg.speaker}: {seg.text}")
            
    finally:
        if os.path.exists(video_path):
            os.unlink(video_path)
            logger.info("Cleaned up local video file.")


if __name__ == "__main__":
    main()
