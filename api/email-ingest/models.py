"""
Email Ingest — Pydantic Models

Internal models for parsed email data. Not stored in Firestore directly —
these are intermediate representations used by the pipeline.
"""

from datetime import date, datetime
from typing import Optional
from pydantic import BaseModel, Field


class ParsedEmail(BaseModel):
    """Parsed email content extracted from the raw Gmail message."""
    message_id: str = Field(..., description="Gmail message ID (used for dedup).")
    thread_id: str = Field(..., description="Gmail thread ID.")
    subject: str = Field(..., description="Email subject line.")
    from_address: str = Field(..., description="Sender email address.")
    date_received: datetime = Field(..., description="When the email was received.")
    horse_name: str = Field(..., description="Horse name extracted from subject.")
    content_date: date = Field(..., description="Date from email body (e.g. '18 May 2026').")
    title: str = Field(..., description="Title from email body.")
    video_url: Optional[str] = Field(None, description="Video CDN URL found in email body.")
    speaker_count: int = Field(1, description="Number of speakers (1 or 2).")
    body_text: str = Field("", description="Plain text body for logging.")


class TranscriptSegment(BaseModel):
    """A single segment of transcribed speech."""
    start_time: float
    end_time: float
    speaker: str = Field(..., description="Mapped speaker name (e.g. 'Andrew Scott').")
    text: str


class TranscriptResult(BaseModel):
    """Full transcript output from Google Speech-to-Text."""
    source: str = Field("google_speech_v1", description="ASR source identifier.")
    model: str = Field("latest_long", description="STT model used.")
    full_text: str = Field(..., description="Full concatenated transcript.")
    segments: list[TranscriptSegment] = Field(default_factory=list)
    speakers: list[dict] = Field(default_factory=list, description="Speaker mappings [{name, label}].")
    confidence: Optional[str] = Field(None, description="LLM reconciliation confidence score.")
    needs_human_review: Optional[bool] = Field(None, description="Flag indicating if transcript requires manual review.")
    review_reason: Optional[str] = Field(None, description="Reason why manual review is needed.")
    reconciliation_changes: Optional[list[dict]] = Field(default_factory=list, description="Detailed change log of edits made during reconciliation.")



class IngestResult(BaseModel):
    """Result of a single email ingestion."""
    message_id: str
    horse_name: str
    horse_microchip: Optional[str] = None
    video_asset_id: Optional[str] = None
    video_public_url: Optional[str] = None
    content_id: Optional[str] = None
    status: str = "pending"  # pending, success, skipped_duplicate, skipped_no_horse, error
    error: Optional[str] = None
