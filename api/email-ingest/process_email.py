#!/usr/bin/env python3
"""Process a specific email by ID for testing."""

import os
import sys
import imaplib
import email
from dotenv import load_dotenv

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from parser import parse_email
from transcriber import Transcriber
from main import _download_video

load_dotenv("/home/evo/.env")

EMAIL_USER = os.getenv("WEXFORD_EMAIL_USER", "alex@evolutionstables.nz")
EMAIL_PASS = os.getenv("WEXFORD_APP_PASSWORD")

def fetch_email_by_id(msg_id: str):
    """Fetch a specific email by IMAP ID and return as dict."""
    mail = imaplib.IMAP4_SSL('imap.gmail.com')
    mail.login(EMAIL_USER, EMAIL_PASS)
    mail.select('INBOX', readonly=True)
    
    status, data = mail.fetch(msg_id.encode(), '(RFC822)')
    if status != 'OK':
        raise RuntimeError(f"Failed to fetch email {msg_id}")
    
    msg = email.message_from_bytes(data[0][1])
    
    # Extract body text
    body_text = ""
    body_html = ""
    if msg.is_multipart():
        for part in msg.walk():
            if part.get_content_type() == 'text/plain' and 'attachment' not in str(part.get('Content-Disposition')):
                body_text = part.get_payload(decode=True).decode('utf-8', errors='replace')
            elif part.get_content_type() == 'text/html' and 'attachment' not in str(part.get('Content-Disposition')):
                body_html = part.get_payload(decode=True).decode('utf-8', errors='replace')
    else:
        body_text = msg.get_payload(decode=True).decode('utf-8', errors='replace')
    
    mail.logout()
    
    # Parse date properly
    from email.utils import parsedate_to_datetime
    try:
        date_received = parsedate_to_datetime(msg.get('Date', ''))
    except:
        from datetime import datetime, timezone
        date_received = datetime.now(timezone.utc)
    
    # Return as dict matching GmailClient format
    return {
        "message_id": msg.get('Message-ID', f"<imap-{msg_id}@gmail.com>"),
        "thread_id": msg.get('Thread-Index', ''),
        "subject": msg.get('Subject', ''),
        "from_address": msg.get('From', ''),
        "date_received": date_received,
        "body_text": body_text,
        "body_html": body_html,
    }

def main():
    if len(sys.argv) < 2:
        print("Usage: python process_email.py <email_id>")
        print("Example: python process_email.py 7873")
        sys.exit(1)
    
    email_id = sys.argv[1]
    print(f"Fetching email ID {email_id}...")
    
    raw_email = fetch_email_by_id(email_id)
    
    print(f"Subject: {raw_email['subject']}")
    print(f"From: {raw_email['from_address']}")
    
    # Parse the email
    parsed = parse_email(raw_email)
    
    print(f"\nParsed:")
    print(f"  Horse: {parsed.horse_name}")
    print(f"  Date: {parsed.content_date}")
    print(f"  Video: {parsed.video_url or 'No'}")
    print(f"  Speakers: {parsed.speaker_count}")
    
    if not parsed.video_url:
        print("\nNo video URL - skipping transcription")
        return
    
    # Download video
    print(f"\nDownloading video from {parsed.video_url}...")
    video_path = _download_video(parsed.video_url)
    print(f"Downloaded to: {video_path}")
    
    # Transcribe
    print(f"\nTranscribing with {parsed.speaker_count} speaker(s)...")
    transcriber = Transcriber(speaker_count=parsed.speaker_count)
    transcript = transcriber.transcribe_video(
        video_path=video_path,
        engine="auto",
        horse_name=parsed.horse_name
    )
    
    print(f"\n=== TRANSCRIPT ===")
    print(f"Full text: {transcript.full_text[:500]}...")
    print(f"\nSegments:")
    for seg in transcript.segments:
        print(f"  [{seg.start_time:.1f}s] {seg.speaker}: {seg.text[:100]}")
    
    # Save to output directory
    output_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "output")
    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, f"transcript_{parsed.horse_name}_{parsed.content_date.isoformat()}.json")
    
    import json
    segments_list = [
        {"start_time": s.start_time, "end_time": s.end_time, "speaker": s.speaker, "text": s.text}
        for s in transcript.segments
    ]
    with open(output_path, "w") as f:
        json.dump({
            "full_text": transcript.full_text,
            "segments": segments_list,
            "source": transcript.source,
            "model": transcript.model,
            "speakers": transcript.speakers
        }, f, indent=2)
    
    print(f"\nSaved transcript to: {output_path}")
    print("\n✅ Email processing complete!")

if __name__ == "__main__":
    main()
