"""
Email Ingest — Cloud Function Entry Point

Triggered by Cloud Scheduler twice daily (09:00, 21:00 NZST).
Checks info@wexfordstables.co.nz for unread video-update emails,
downloads videos, uploads to GCS via Assets API, transcribes via
Google STT, and stores transcripts via SSOT API.

Architecture:
  This function calls the SSOT and Assets APIs via HTTP.
  It does NOT write to Firestore or GCS directly (except STT temp bucket).
  This respects Core Law #1: api/ is the only data writer.
"""

import logging
import os
import tempfile
import uuid
from datetime import timezone

import functions_framework
import requests
from flask import Request, jsonify

from gmail_client import GmailClient
from models import IngestResult
from parser import parse_email, get_speaker_names
from transcriber import Transcriber

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ─── CONFIG ──────────────────────────────────────────────────────

# Service account for Gmail API (domain-wide delegation to info@wexfordstables.co.nz)
GMAIL_CREDENTIALS_PATH = os.getenv(
    "GMAIL_CREDENTIALS_PATH",
    "/secrets/gmail-service-account.json",
)
DELEGATE_EMAIL = os.getenv(
    "DELEGATE_EMAIL",
    "info@wexfordstables.co.nz",
)

# Internal API URLs (Cloud Functions in same project)
SSOT_API_URL = os.getenv(
    "SSOT_API_URL",
    "https://australia-southeast1-evolution-engine.cloudfunctions.net/ssot",
)
ASSETS_API_URL = os.getenv(
    "ASSETS_API_URL",
    "https://australia-southeast1-evolution-engine.cloudfunctions.net/assets",
)

# Sender to monitor
FROM_ADDRESS = os.getenv("FROM_ADDRESS", "info@wexfordstables.co.nz")
MAX_EMAILS = int(os.getenv("MAX_EMAILS", "5"))


@functions_framework.http
def email_ingest(request: Request):
    """
    Cloud Function entry point.

    GET  — health check, returns status.
    POST — trigger a full scan of unread emails.
    """
    # Handle CORS preflight
    if request.method == "OPTIONS":
        response = jsonify({})
        response.headers.add("Access-Control-Allow-Origin", "*")
        response.headers.add("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        response.headers.add("Access-Control-Allow-Headers", "Content-Type")
        return response, 200

    if request.method == "GET":
        return jsonify({
            "status": "healthy",
            "delegate_email": DELEGATE_EMAIL,
            "from_address": FROM_ADDRESS,
        }), 200

    if request.method != "POST":
        return jsonify({"error": "Method not allowed. Use POST to trigger scan."}), 405

    # ── MAIN PIPELINE ──────────────────────────────────────────

    logger.info(f"Starting email ingest scan for {FROM_ADDRESS}")

    # Verify credentials exist
    if not os.path.exists(GMAIL_CREDENTIALS_PATH):
        logger.error(f"Gmail credentials not found at {GMAIL_CREDENTIALS_PATH}")
        return jsonify({"error": "Gmail credentials not configured"}), 500

    try:
        gmail = GmailClient(GMAIL_CREDENTIALS_PATH, DELEGATE_EMAIL)
        emails = gmail.get_unread_emails(FROM_ADDRESS, max_results=MAX_EMAILS)
    except Exception as e:
        logger.error(f"Gmail fetch failed: {e}")
        return jsonify({"error": f"Gmail fetch failed: {str(e)}"}), 500

    if not emails:
        logger.info("No unread emails to process")
        return jsonify({"status": "no_emails", "processed": 0}), 200

    results: list[dict] = []
    for raw_email in emails:
        result = _process_email(raw_email, gmail)
        results.append(result.model_dump())

    # Summary
    success_count = sum(1 for r in results if r["status"] == "success")
    error_count = sum(1 for r in results if r["status"] == "error")
    skipped_count = sum(1 for r in results if r["status"] in ("skipped_duplicate", "skipped_no_horse", "skipped_no_video"))

    summary = {
        "status": "complete",
        "total": len(results),
        "success": success_count,
        "skipped": skipped_count,
        "errors": error_count,
        "results": results,
    }

    logger.info(f"Scan complete: {success_count} success, {skipped_count} skipped, {error_count} errors")
    return jsonify(summary), 200


def _process_email(raw_email: dict, gmail: GmailClient) -> IngestResult:
    """
    Process a single email through the full pipeline:
    Parse → Resolve horse → Download video → Upload → Transcribe → Store.
    """
    message_id = raw_email["message_id"]
    result = IngestResult(
        message_id=message_id,
        horse_name="Unknown",
        status="pending",
    )

    try:
        # Step 1: Parse email
        parsed = parse_email(raw_email)
        result.horse_name = parsed.horse_name
        logger.info(f"Processing: {parsed.subject} (horse={parsed.horse_name})")

        # Step 2: Check dedup — does content already exist for this email?
        dedup_check = requests.get(
            f"{SSOT_API_URL}/content",
            params={"horse_microchip": "__dedup__"},  # We'll check differently
            timeout=10,
        )
        # Actually check by querying for source_email_id
        # Since SSOT doesn't have a direct "get by source_email_id" endpoint,
        # we check by trying to create — the SSOT will 409 if duplicate.
        # We'll handle that in Step 7.

        # Step 3: Resolve horse name → microchip
        horse_resp = requests.get(f"{SSOT_API_URL}/horses", timeout=10)
        if horse_resp.status_code != 200:
            raise RuntimeError(f"Failed to list horses: {horse_resp.status_code}")

        horses = horse_resp.json()
        # Client-side name match (SSOT doesn't have name-search endpoint)
        matched = [
            h for h in horses
            if parsed.horse_name.lower() in h.get("name", "").lower()
        ]
        if not matched:
            logger.warning(f"Horse '{parsed.horse_name}' not found in SSOT — skipping")
            result.status = "skipped_no_horse"
            result.error = f"Horse '{parsed.horse_name}' not registered in system"
            # Still mark as read so we don't retry forever
            gmail.mark_read(message_id)
            return result

        horse = matched[0]
        microchip = horse["microchip"]
        result.horse_microchip = microchip
        logger.info(f"Resolved {parsed.horse_name} → microchip {microchip}")

        # Step 4: Check for video URL
        if not parsed.video_url:
            logger.warning("No video URL found in email — skipping video update processing")
            result.status = "skipped_no_video"
            result.error = "No video URL in email"
            # Still mark as read so we don't retry forever
            gmail.mark_read(message_id)
            return result

        video_path = _download_video(parsed.video_url)
        logger.info(f"Video downloaded: {video_path}")

        try:
            # Step 5: Upload video to GCS via Assets API
            asset_id, public_url = _upload_to_assets(
                video_path, microchip, parsed
            )
            result.video_asset_id = asset_id
            result.video_public_url = public_url
            logger.info(f"Video uploaded: asset_id={asset_id}")

            # Step 6: Transcribe
            transcriber = Transcriber(speaker_count=parsed.speaker_count)
            force_audit = os.getenv("FORCE_AUDIT", "false").lower() == "true"
            transcript = transcriber.transcribe_video(
                video_path,
                horse_name=parsed.horse_name,
                force_audit=force_audit
            )
            logger.info(f"Transcription complete: {len(transcript.segments)} segments")

            # Step 7: Store transcript via SSOT API
            content_id = _store_content(
                parsed=parsed,
                microchip=microchip,
                asset_id=asset_id,
                transcript=transcript,
            )
            result.content_id = content_id
            result.status = "success"
            logger.info(f"Content stored: content_id={content_id}")

        finally:
            # Clean up temp video file
            if os.path.exists(video_path):
                os.unlink(video_path)

        # Step 8: Mark email as read
        gmail.mark_read(message_id)

    except Exception as e:
        logger.error(f"Failed to process {message_id}: {e}")
        result.status = "error"
        result.error = str(e)
        # Try to mark as read even on error to avoid infinite retry loops
        try:
            gmail.mark_read(message_id)
        except Exception:
            pass

    return result


def _download_video(url: str) -> str:
    """Download a video from a URL to a temp file. Returns local path."""
    ext = ".mp4"
    if ".mov" in url.lower():
        ext = ".mov"
    elif ".webm" in url.lower():
        ext = ".webm"

    tmp_path = os.path.join(
        tempfile.gettempdir(),
        f"email-video-{uuid.uuid4().hex[:8]}{ext}",
    )

    logger.info(f"Downloading video: {url[:80]}...")
    resp = requests.get(url, stream=True, timeout=120)
    resp.raise_for_status()

    with open(tmp_path, "wb") as f:
        for chunk in resp.iter_content(chunk_size=8192):
            f.write(chunk)

    size_mb = os.path.getsize(tmp_path) / (1024 * 1024)
    logger.info(f"Downloaded: {size_mb:.1f}MB → {tmp_path}")
    return tmp_path


def _upload_to_assets(video_path: str, microchip: str, parsed) -> tuple[str, str]:
    """
    Upload video to GCS via Assets API.
    Returns (asset_id, public_url).
    """
    filename = os.path.basename(video_path)
    date_str = parsed.content_date.isoformat()
    tags = f"video,update,{parsed.horse_name},{date_str}"

    with open(video_path, "rb") as f:
        resp = requests.post(
            f"{ASSETS_API_URL}/upload",
            files={"file": (filename, f, "video/mp4")},
            data={
                "entity_type": "horse",
                "entity_id": microchip,
                "tags": tags,
                "alt": f"Video update for {parsed.horse_name} — {parsed.title}",
                "uploaded_by": "email-ingest",
            },
            timeout=120,
        )

    if resp.status_code not in (200, 201):
        raise RuntimeError(f"Assets API upload failed: {resp.status_code} {resp.text}")

    data = resp.json()
    return data["id"], data.get("public_url", "")


def _store_content(
    parsed,
    microchip: str,
    asset_id: str,
    transcript,
) -> str:
    """
    Store transcript as a content record via SSOT API.
    Returns the content document ID.
    """
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
        "confidence": getattr(transcript, "confidence", None),
        "needs_human_review": getattr(transcript, "needs_human_review", None),
        "review_reason": getattr(transcript, "review_reason", None),
        "reconciliation_changes": getattr(transcript, "reconciliation_changes", []),
    }

    resp = requests.post(
        f"{SSOT_API_URL}/content",
        json=payload,
        timeout=30,
    )

    if resp.status_code == 409:
        # Duplicate — already exists
        existing = resp.json()
        logger.info(f"Content already exists: {existing.get('existing_id')}")
        return existing.get("existing_id", "")

    if resp.status_code not in (200, 201):
        raise RuntimeError(f"SSOT content creation failed: {resp.status_code} {resp.text}")

    data = resp.json()
    return data.get("id", "")
