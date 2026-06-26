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
    r'https?://[^\s"\'<>]+?\.(?:mp4|mov|webm|avi|mkv|mp3|m4a)',
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

    # Strip HTML if the body contains HTML tags (some emails are single-part text/html,
    # so body_text itself can be HTML — not just body_html)
    if body and "<html" in body.lower() or "<!doctype" in body.lower() or "<p>" in body.lower():
        body = re.sub(r"<[^>]*>", " ", body)
        body = re.sub(r"\s+", " ", body).strip()

    horse_name = _clean_horse_display(_extract_horse_name(subject))
    date_received = raw_email.get("date_received", datetime.now())
    content_date = _extract_date(body, subject=subject, date_received=date_received)
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
    Handles multiple formats:
      - "Video Update for {HorseName}"
      - "Video Update: {HorseName}"
      - "Video Update - {HorseName}"
      - "Race Acceptance - {HorseName} - {date} - {venue}"
      - "Update for {HorseName}"
    """
    # Try "Audio Update: X" or "Audio Update - X"
    match = re.search(r"Audio\s+Update\s*[:\-]\s*(.+?)(?:\s*$)", subject, re.IGNORECASE)
    if match:
        return match.group(1).strip()

    # Try "Video Update for/with X" or "Video Update: X" or "Video Update - X"
    match = re.search(r"Video\s+Update\s+(?:for|with)\s+(.+?)(?:\s*$)", subject, re.IGNORECASE)
    if match:
        return match.group(1).strip()
    match = re.search(r"Video\s+Update\s*[:\-]\s*(.+?)(?:\s*$)", subject, re.IGNORECASE)
    if match:
        return match.group(1).strip()

    # Try "Race Acceptance/Result - {HorseName} - {date} - {venue}"
    match = re.search(r"Race\s+(?:Acceptance|Result)\s*-\s*(.+?)\s*-", subject, re.IGNORECASE)
    if match:
        return match.group(1).strip()

    # Try "Update for X" or "Update: X" or "Update - X"
    match = re.search(r"Update\s+for\s+(.+?)(?:\s*$)", subject, re.IGNORECASE)
    if match:
        return match.group(1).strip()
    match = re.search(r"^Update\s*[:\-]\s*(.+?)(?:\s*$)", subject, re.IGNORECASE)
    if match:
        return match.group(1).strip()

    # Fallback: use the whole subject minus common prefixes
    cleaned = re.sub(r"^(?:VIDEO\s+)?Update\s*(?:for\s*)?", "", subject, flags=re.IGNORECASE).strip()
    cleaned = re.sub(r"\s*\(NZ\)\s*$", "", cleaned, flags=re.IGNORECASE).strip()
    return cleaned or "Unknown"


def _clean_horse_display(name: str) -> str:
    """Normalize horse name for storage (strip regional suffixes)."""
    return re.sub(r"\s*\(NZ\)\s*$", "", name.strip(), flags=re.IGNORECASE).strip()


_MONTH_PATTERN = r"(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*"


def _parse_day_month_year(day_month: str, year: int) -> date | None:
    for fmt in ("%d %B %Y", "%d %b %Y"):
        try:
            return datetime.strptime(f"{day_month} {year}", fmt).date()
        except ValueError:
            continue
    return None


def _extract_date(body: str, subject: str = "", date_received: datetime | None = None) -> date:
    """
    Extract date from email body, with subject-line fallback for race emails.
    Pattern: "Date: 18 May 2026"
    """
    match = re.search(
        rf"Date:\s*(\d{{1,2}}\s+{_MONTH_PATTERN}\s+\d{{4}})",
        body,
        re.IGNORECASE,
    )
    if match:
        date_str = match.group(1)
        for fmt in ("%d %B %Y", "%d %b %Y"):
            try:
                return datetime.strptime(date_str, fmt).date()
            except ValueError:
                continue

    # Try ISO format fallback
    match = re.search(r"Date:\s*(\d{4}-\d{2}-\d{2})", body)
    if match:
        try:
            return datetime.strptime(match.group(1), "%Y-%m-%d").date()
        except ValueError:
            pass

    # Race emails often omit body Date: — use "14 Mar" from subject
    if subject:
        match = re.search(
            rf"-\s*(\d{{1,2}}\s+{_MONTH_PATTERN})\s*-",
            subject,
            re.IGNORECASE,
        )
        if match:
            year = date_received.year if date_received else date.today().year
            parsed = _parse_day_month_year(match.group(1), year)
            if parsed:
                return parsed

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


_WRAPPER_HOSTS = (
    "urldefense.proofpoint.com",
    "urldefense.com",
    "mimecastprotect.com",
    "protect-us.mimecast.com",
    "safelinks.protection.outlook.com",
)


def _is_skippable_video_url(lower_url: str) -> bool:
    image_and_doc_extensions = (
        ".jpg", ".jpeg", ".png", ".gif", ".webp", ".svg",
        ".pdf", ".docx", ".csv", ".xlsx", ".css", ".js",
    )
    if any(lower_url.endswith(ext) for ext in image_and_doc_extensions):
        return True

    skip_keywords = [
        "/unsubscribe", "unsubscribe",
        "/portal",
        "pstmrk.it", "postmark",
        "w3.org",
        "/assets/", "/images/",
    ]
    if any(keyword in lower_url for keyword in skip_keywords):
        return True

    if lower_url.endswith("/media/video") or lower_url.endswith("/media/video/"):
        return True

    return any(host in lower_url for host in _WRAPPER_HOSTS)


def _video_url_score(url: str) -> int:
    lower_url = url.lower()
    score = 0
    if "cdn2.prism.horse/media/" in lower_url or "prism.horse/media/" in lower_url:
        score += 100
    if lower_url.endswith((".mp4", ".mp3", ".m4a", ".mov")):
        score += 20
    if "cdn" in lower_url or "prism.horse" in lower_url:
        score += 10
    return score


def _extract_video_url(body: str) -> str | None:
    """Extract the best video URL from the email body (prefer Prism CDN)."""
    candidates: list[str] = []
    for pattern in VIDEO_URL_PATTERNS:
        matches = re.findall(pattern, body, re.IGNORECASE)
        for match in matches:
            url = match.strip().rstrip(".,;:!?")
            if url and len(url) > 10 and not _is_skippable_video_url(url.lower()):
                candidates.append(url)

    if not candidates:
        return None

    return max(candidates, key=_video_url_score)


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
