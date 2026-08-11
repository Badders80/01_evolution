import os
import sys
import time
import json
import sqlite3
import requests
import logging
from datetime import datetime
from dotenv import load_dotenv
from google.auth import default
from google.auth.transport.requests import Request

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import our unified pipeline modules
from archive_media import (
    archive_enabled,
    archive_from_parsed,
    delete_temp_enabled,
    infer_media_kind,
    normalize_horse_slug,
)
from parser import parse_email
from transcriber import Transcriber
from main import _download_video
from gmail_client import GmailClient

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv("/home/evo/.env")

# APIs config
SSOT_API_URL = "https://australia-southeast1-evolution-engine.cloudfunctions.net/ssot"
ASSETS_API_URL = "https://australia-southeast1-evolution-engine.cloudfunctions.net/assets"

# Local-first data paths (configurable via env vars, defaults inside workspace)
_DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
DB_PATH = os.getenv("INGEST_DB_PATH", os.path.join(_DATA_DIR, "ledger.sqlite"))
CATALOG_PATH = os.getenv("INGEST_CATALOG_PATH", os.path.join(_DATA_DIR, "content-index.ndjson"))
LOCAL_ASSETS_DIR = os.getenv("INGEST_ASSETS_DIR", os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", "_assets", "horses"))

# Credentials
WEXFORD_EMAIL_USER = os.getenv("WEXFORD_EMAIL_USER", "alex@evolutionstables.nz")
GMAIL_CREDENTIALS_PATH = os.getenv("GMAIL_CREDENTIALS_PATH", "/home/evo/secrets/gmail-service-account.json")


def get_auth_headers(target_audience=None):
    """Get authentication headers for Cloud Functions API calls."""
    try:
        import subprocess
        if target_audience:
            result = subprocess.run(
                ['gcloud', 'auth', 'print-identity-token', '--audiences', target_audience],
                capture_output=True, text=True, check=True
            )
            token = result.stdout.strip()
            return {"Authorization": f"Bearer {token}"}
        else:
            credentials, project = default()
            credentials.refresh(Request())
            token = credentials.token
            return {"Authorization": f"Bearer {token}"}
    except Exception as e:
        logger.warning(f"Failed to get auth headers: {e}")
    
    try:
        credentials, project = default()
        credentials.refresh(Request())
        token = credentials.token
        return {"Authorization": f"Bearer {token}"}
    except Exception as e:
        logger.warning(f"Failed to get fallback auth headers: {e}")
        return {}


def get_latest_wexford_email_api():
    """Fetch the latest Wexford or Prudentia email via Gmail API."""
    if not os.path.exists(GMAIL_CREDENTIALS_PATH):
        raise FileNotFoundError(
            f"Gmail credentials JSON file not found at {GMAIL_CREDENTIALS_PATH}. "
            "Please create a service account and save the JSON key file there."
        )

    logger.info(f"Initializing Gmail API Client for {WEXFORD_EMAIL_USER} using credentials at {GMAIL_CREDENTIALS_PATH}...")
    client = GmailClient(GMAIL_CREDENTIALS_PATH, WEXFORD_EMAIL_USER)
    
    # Query: from Wexford email OR containing "Prudentia" keyword
    query = 'from:info@wexfordstables.co.nz OR "Prudentia"'
    logger.info(f"Searching Gmail API with query: {query}")
    
    try:
        # Get list of messages matching query
        results = client.service.users().messages().list(
            userId="me",
            q=query,
            maxResults=1
        ).execute()
        
        messages = results.get("messages", [])
        if not messages:
            logger.info("No matching emails found via Gmail API")
            sys.exit(0)
            
        message_id = messages[0]["id"]
        logger.info(f"Fetching message details for message ID: {message_id}")
        
        email_data = client._get_message(message_id)
        if not email_data:
            raise RuntimeError("Failed to parse retrieved email data")
            
        return email_data, client
        
    except Exception as e:
        logger.error(f"Gmail API query failed: {e}")
        raise


def resolve_horse_microchip(horse_name: str) -> str:
    """Query SSOT API to match horse name to microchip."""
    logger.info(f"Resolving microchip for horse name: {horse_name}")
    
    headers = get_auth_headers(SSOT_API_URL)
    resp = requests.get(f"{SSOT_API_URL}/horses", headers=headers, timeout=10)
    
    if resp.status_code != 200:
        raise RuntimeError(f"SSOT API request failed: {resp.status_code} {resp.text}")
        
    horses = resp.json()
    matched = [h for h in horses if horse_name.lower() in h.get("name", "").lower()]
    
    if not matched:
        raise ValueError(f"Horse '{horse_name}' not found in SSOT reference database")
        
    microchip = matched[0]["microchip"]
    logger.info(f"Resolved '{horse_name}' -> microchip '{microchip}'")
    return microchip


def upload_to_assets_api(video_path, microchip, parsed):
    """Upload video file to Assets API (with local fallback)."""
    filename = os.path.basename(video_path)
    date_str = parsed.content_date.isoformat()
    tags = f"video,update,{parsed.horse_name},{date_str}"
    
    headers = get_auth_headers(ASSETS_API_URL)
    
    try:
        logger.info(f"Uploading video {video_path} to Assets API for microchip {microchip}...")
        with open(video_path, "rb") as f:
            resp = requests.post(
                f"{ASSETS_API_URL}/upload",
                headers=headers,
                files={"file": (filename, f, "video/mp4")},
                data={
                    "entity_type": "horse",
                    "entity_id": microchip,
                    "tags": tags,
                    "alt": f"Video update for {parsed.horse_name} — {parsed.title}",
                    "uploaded_by": "email-ingest-api"
                },
                timeout=120
            )
            
        if resp.status_code in (200, 201):
            data = resp.json()
            logger.info(f"Successfully uploaded to Assets API. Asset ID: {data['id']}")
            return data["id"]
        else:
            logger.warning(f"Assets API returned error: {resp.status_code} {resp.text}")
            
    except Exception as e:
        logger.error(f"Error calling Assets API: {e}")
        
    # Local fallback
    logger.info("Using local assets catalog fallback...")
    local_dir = LOCAL_ASSETS_DIR
    os.makedirs(local_dir, exist_ok=True)
    local_path = os.path.join(local_dir, filename)
    
    import shutil
    shutil.copy2(video_path, local_path)
    logger.info(f"Copied video to local assets folder: {local_path}")
    
    fallback_id = f"local-assets-{int(time.time())}"
    return fallback_id


def store_content_api(parsed, microchip, asset_id, transcript):
    """Create a new transcript content record via SSOT API."""
    headers = get_auth_headers(SSOT_API_URL)
    
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
                "text": s.text
            }
            for s in transcript.segments
        ],
        "source": transcript.source,
        "source_email_id": parsed.message_id,
        "asset_ids": [asset_id] if asset_id else [],
        "status": "published",
        "confidence": getattr(transcript, "confidence", None),
        "needs_human_review": getattr(transcript, "needs_human_review", None),
        "review_reason": getattr(transcript, "review_reason", None),
        "reconciliation_changes": getattr(transcript, "reconciliation_changes", [])
    }
    
    try:
        logger.info("Storing transcript content in SSOT API...")
        resp = requests.post(
            f"{SSOT_API_URL}/content",
            headers=headers,
            json=payload,
            timeout=30
        )
        
        if resp.status_code == 409:
            data = resp.json()
            logger.info(f"Duplicate content detected. Existing ID: {data.get('existing_id')}")
            return data.get("existing_id")
        elif resp.status_code in (200, 201):
            data = resp.json()
            logger.info(f"Successfully stored content. ID: {data['id']}")
            return data["id"]
        else:
            logger.warning(f"SSOT API returned error: {resp.status_code} {resp.text}")
    except Exception as e:
        logger.error(f"Error calling SSOT content API: {e}")
        
    return f"local-content-{int(time.time())}"


def store_in_local_sqlite(parsed, transcript):
    """Store raw details in local SQLite ledger."""
    try:
        if not os.path.exists(DB_PATH):
            logger.warning(f"Local SQLite ledger DB not found at: {DB_PATH}. Skipping local SQL log.")
            return
            
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Check if tables exist
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='emails';")
        if not cursor.fetchone():
            logger.info("Initializing 'emails' table in local SQLite ledger...")
            cursor.execute("""
                CREATE TABLE emails (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    message_id TEXT UNIQUE,
                    subject TEXT,
                    sender TEXT,
                    date_received TEXT,
                    horse_name TEXT,
                    body_text TEXT,
                    transcript TEXT,
                    asset_id TEXT,
                    content_id TEXT,
                    created_at TEXT
                );
            """)
            conn.commit()
            
        # Check duplicate
        cursor.execute("SELECT id FROM emails WHERE message_id = ?", (parsed.message_id,))
        row = cursor.fetchone()
        
        if row:
            logger.info(f"Email already exists in SQLite DB (ID: {row[0]}). Skipping duplicate SQL log.")
        else:
            logger.info("Inserting record into local SQLite emails ledger...")
            cursor.execute(
                """
                INSERT INTO emails (
                    message_id, subject, sender, date_received, 
                    horse_name, body_text, transcript, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?);
                """,
                (
                    parsed.message_id,
                    parsed.subject,
                    parsed.from_address,
                    parsed.content_date.isoformat(),
                    parsed.horse_name,
                    parsed.body_text,
                    transcript.full_text,
                    datetime.now().isoformat()
                )
            )
            conn.commit()
            
            # NDJSON ledger backup for frontend platform updates
            catalog_path = CATALOG_PATH
            catalog_entry = {
                "message_id": parsed.message_id,
                "subject": parsed.subject,
                "date": parsed.content_date.isoformat(),
                "horse": parsed.horse_name,
                "transcript": transcript.full_text
            }
            with open(catalog_path, "a") as cat_f:
                cat_f.write(json.dumps(catalog_entry) + "\n")
            logger.info("Successfully appended event to catalog/content-index.ndjson.")
            
        conn.close()
    except Exception as e:
        logger.error(f"Error storing in local SQLite: {e}")


def main():
    logger.info("=== Wexford Email Ingestion Trigger (Gmail API) ===")
    
    # 1. Fetch latest raw email from inbox using Gmail API
    try:
        raw_email, gmail_client = get_latest_wexford_email_api()
    except Exception as e:
        logger.error(f"Failed to fetch email from Gmail API: {e}")
        sys.exit(1)
        
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
        
        # Mark as read
        gmail_client.mark_read(parsed.message_id)
        
        logger.info("Successfully ingested text-only communication.")
        logger.info(f"Content ID: {content_id}")
        logger.info("=== SUCCESS (TEXT-ONLY) ===")
        sys.exit(0)
        
    # 4. Download video using main module download helper
    video_path = _download_video(parsed.video_url)
    horse_slug = normalize_horse_slug(parsed.horse_name)
    media_kind = infer_media_kind(parsed.video_url, video_path)
    
    try:
        # 5. Transcribe
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

        if archive_enabled():
            archive_from_parsed(video_path, horse_slug, parsed)
        
        # 8. Store in local SQLite DB
        store_in_local_sqlite(parsed, transcript)
        
        # Mark email as read via API
        gmail_client.mark_read(parsed.message_id)
        
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
        if delete_temp_enabled() and os.path.exists(video_path):
            os.unlink(video_path)
            logger.info("Cleaned up local video file.")


if __name__ == "__main__":
    main()
