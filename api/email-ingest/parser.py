"""
Email Body Parser

Parses the structured text of Wexford Stables video-update emails.
Does NOT use LLM — the format is predictable enough for regex.

Expected format:
    Subject: Video Update for {horse_name}
    Body:
      Date: 18 May 2026
      Title: VIDEO Update - 18 May 26
      [video link — CDN URL, usually .mp4]
      [speaker context: "Lance O'Sullivan & Andrew Scott" = 2 speakers, else solo]
"""

import re
import logging
from datetime import date, datetime

from models import ParsedEmail

logger = logging.getLogger(__name__)

# Known speaker patterns
TWO_SPEAKER_PATTERNS = [
    r"Lance\s+O'?Sullivan\s*[&and]+\s*Andrew\s+Scott",
    r"Andrew\s+Scott\s*[&and]+\s*Lance\s+O'?Sullivan",
]

# Video URL patterns
VIDEO_URL_PATTERNS = [
    r'https?://[^\s"\'<>]+?\.(?:mp4|mov|webm|avi|mkv)',
    r'https?://[^\s"\'<>]*?(?:video|cdn|prism\.horse|vimeo|wistia)[^\s"\'<>]*',
    r'https?://[^\s"\'<>]*?youtube[^\s"\'<>]*',
]


def parse_email(raw_email: dict) -> ParsedEmail:
    """
    Parse a raw Gmail message dict into a structured ParsedEmail.

    Args:
        raw_email: Dict from GmailClient.get_unread_emails() with keys:
            message_id, thread_id, subject, from_address, date_received,
            body_text, body_html

    Returns:
        ParsedEmail with extracted horse_name, content_date, title, video_url, speaker_count.
    """
    subject = raw_email.get("subject", "")
    body = raw_email.get("body_text", "") or raw_email.get("body_html", "")

    # Strip HTML if we got HTML
    if raw_email.get("body_html") and not raw_email.get("body_text"):
        body = re.sub(r"<[^>]*>", " ", body)
        body = re.sub(r"\s+", " ", body).strip()

    horse_name = _extract_horse_name(subject)
    content_date = _extract_date(body)
    title = _extract_title(body)
    video_url = _extract_video_url(body)
    speaker_count = _detect_speaker_count(body)

    logger.info(
        f"Parsed email: horse={horse_name}, date={content_date}, "
        f"speakers={speaker_count}, video={'yes' if video_url else 'no'}"
    )

    return ParsedEmail(
        message_id=raw_email["message_id"],
        thread_id=raw_email.get("thread_id", ""),
        subject=subject,
        from_address=raw_email.get("from_address", ""),
        date_received=raw_email.get("date_received", datetime.now()),
        horse_name=horse_name,
        content_date=content_date,
        title=title,
        video_url=video_url,
        speaker_count=speaker_count,
        body_text=body[:5000],
    )


def _extract_horse_name(subject: str) -> str:
    """
    Extract horse name from subject line.
    Pattern: "Video Update for {HorseName}"
    """
    # Try "Video Update for X"
    match = re.search(r"Video\s+Update\s+for\s+(.+?)(?:\s*$)", subject, re.IGNORECASE)
    if match:
        return match.group(1).strip()

    # Try "Update for X"
    match = re.search(r"Update\s+for\s+(.+?)(?:\s*$)", subject, re.IGNORECASE)
    if match:
        return match.group(1).strip()

    # Fallback: use the whole subject minus common prefixes
    cleaned = re.sub(r"^(?:VIDEO\s+)?Update\s*(?:for\s*)?", "", subject, flags=re.IGNORECASE).strip()
    return cleaned or "Unknown"


def _extract_date(body: str) -> date:
    """
    Extract date from email body.
    Pattern: "Date: 18 May 2026"
    """
    match = re.search(r"Date:\s*(\d{1,2}\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{4})", body, re.IGNORECASE)
    if match:
        try:
            return datetime.strptime(match.group(1), "%d %B %Y").date()
        except ValueError:
            pass
        try:
            return datetime.strptime(match.group(1), "%d %b %Y").date()
        except ValueError:
            pass

    # Try ISO format fallback
    match = re.search(r"Date:\s*(\d{4}-\d{2}-\d{2})", body)
    if match:
        try:
            return datetime.strptime(match.group(1), "%Y-%m-%d").date()
        except ValueError:
            pass

    logger.warning("Could not parse date from email body, using today")
    return date.today()


def _extract_title(body: str) -> str:
    """
    Extract title from email body.
    Pattern: "Title: VIDEO Update - 18 May 26"
    """
    match = re.search(r"Title:\s*(.+?)(?:\n|$)", body, re.IGNORECASE)
    if match:
        return match.group(1).strip()
    return "Video Update"


def _extract_video_url(body: str) -> str | None:
    """Extract the first video URL from the email body."""
    for pattern in VIDEO_URL_PATTERNS:
        matches = re.findall(pattern, body, re.IGNORECASE)
        for match in matches:
            url = match.strip().rstrip(".,;:!?")
            if url and len(url) > 10:
                return url
    return None


def _detect_speaker_count(body: str) -> int:
    """
    Detect number of speakers from email body.
    If "Lance O'Sullivan & Andrew Scott" (or variants) appear → 2 speakers.
    Otherwise → 1 speaker (Andrew Scott solo).
    """
    for pattern in TWO_SPEAKER_PATTERNS:
        if re.search(pattern, body, re.IGNORECASE):
            return 2
    return 1


def get_speaker_names(speaker_count: int) -> list[str]:
    """
    Return the speaker name list based on count.
    Rule: 1 speaker = Andrew Scott. 2 speakers = Andrew (first), Lance (second).
    """
    if speaker_count == 2:
        return ["Andrew Scott", "Lance O'Sullivan"]
    return ["Andrew Scott"]
