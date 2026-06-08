"""
Evolution API — Shared Pydantic Models

These models are the single source of truth for data validation.
They mirror the JSON Schemas in dna/schemas/ exactly.
Every Cloud Function imports from this package.
"""

from datetime import date, datetime
from typing import Literal, Optional
from pydantic import BaseModel, Field, field_validator
import re


# ─── Horse ────────────────────────────────────────────────────────────────────

class HorseCreate(BaseModel):
    """Payload for creating a new horse record."""
    microchip: str = Field(
        ...,
        pattern=r"^\d{15}$",
        description="NZ microchip number (15 digits). The durable anchor. Never changes.",
        examples=["985125000126462"],
    )
    life_number: Optional[str] = Field(
        None,
        pattern=r"^NZ\d{8}$",
        description="NZTR life number. e.g. NZ00427416",
    )
    loveracing_id: Optional[int] = Field(
        None,
        description="HorseID on loveracing.nz. Used to construct profile URL.",
    )
    name: str = Field(
        ...,
        description="Registered horse name including country suffix and year.",
        examples=["Prudentia (NZ) 2021"],
    )
    name_slug: Optional[str] = Field(
        None,
        description="URL-safe slug. e.g. 'Prudentia-NZ-2021'",
    )
    foaling_date: date = Field(
        ...,
        description="Date of birth.",
    )
    sex: Literal["colt", "filly", "gelding", "mare", "stallion", "horse"]
    colour: Optional[str] = Field(None, examples=["Bay", "Chestnut", "Brown", "Grey", "Black"])
    sire_id: Optional[str] = Field(None, description="Reference to sire horse document ID.")
    sire_name: Optional[str] = Field(None, examples=["PROISIR (AUS) 2009"])
    dam_id: Optional[str] = Field(None, description="Reference to dam horse document ID.")
    dam_name: Optional[str] = Field(None, examples=["LITTLE BIT IRISH (NZ) 2012"])
    family_number: Optional[str] = Field(None, description="Stud Book family number.")
    dna_typed: bool = Field(False, description="Whether the horse has been DNA typed.")
    pv: bool = Field(False, description="Whether the horse has been parentage verified.")
    breeder: Optional[str] = Field(None, examples=["Golden Eye Trust"])
    left_shoulder_brand: Optional[str] = Field(None, examples=["KB INSIDE CIRCLE"])
    right_shoulder_brand: Optional[str] = Field(None, examples=["85 OVER 1"])
    trainer_id: Optional[str] = Field(None, description="Reference to current trainer document ID.")
    status: Literal["active", "retired", "deceased"] = Field("active")


class Horse(HorseCreate):
    """Full horse record with server-generated fields."""
    id: str = Field(..., description="Firestore document ID")
    image_url: Optional[str] = Field(None, description="Primary image GCS URL.")
    age: Optional[int] = Field(None, description="Current age in years. Computed from foaling_date.")
    created_at: datetime
    updated_at: datetime


class HorseUpdate(BaseModel):
    """Payload for updating a horse record. All fields optional."""
    name: Optional[str] = None
    life_number: Optional[str] = None
    loveracing_id: Optional[int] = None
    foaling_date: Optional[date] = None
    sex: Optional[Literal["colt", "filly", "gelding", "mare", "stallion", "horse"]] = None
    colour: Optional[str] = None
    sire_id: Optional[str] = None
    sire_name: Optional[str] = None
    dam_id: Optional[str] = None
    dam_name: Optional[str] = None
    family_number: Optional[str] = None
    dna_typed: Optional[bool] = None
    pv: Optional[bool] = None
    breeder: Optional[str] = None
    left_shoulder_brand: Optional[str] = None
    right_shoulder_brand: Optional[str] = None
    trainer_id: Optional[str] = None
    image_url: Optional[str] = None
    status: Optional[Literal["active", "retired", "deceased"]] = None


# ─── Owner ────────────────────────────────────────────────────────────────────

class OwnerCreate(BaseModel):
    """Payload for creating a new owner record."""
    name: str = Field(..., description="Full legal name.", examples=["Golden Eye Trust"])
    email: str = Field(..., description="Primary contact email.")
    phone: Optional[str] = Field(None, examples=["+64 21 123 4567"])
    type: Literal["individual", "syndicate", "corporate"] = Field("individual")
    address: Optional[str] = Field(None, description="Physical address for legal documents.")
    bank_account: Optional[str] = Field(None, description="Bank account for distributions.")
    ird_number: Optional[str] = Field(None, description="IRD number for tax purposes.")


class Owner(OwnerCreate):
    """Full owner record with server-generated fields."""
    id: str
    created_at: datetime
    updated_at: datetime


class OwnerUpdate(BaseModel):
    """Payload for updating an owner record. All fields optional."""
    name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    type: Optional[Literal["individual", "syndicate", "corporate"]] = None
    address: Optional[str] = None
    bank_account: Optional[str] = None
    ird_number: Optional[str] = None


# ─── Trainer ──────────────────────────────────────────────────────────────────

class TrainerCreate(BaseModel):
    """Payload for creating a new trainer record."""
    name: str = Field(..., examples=["Sam Spratt"])
    stable_name: str = Field(..., examples=["Evolution Stables"])
    location: str = Field(..., examples=["Cambridge, NZ"])
    email: str = Field(...)
    phone: Optional[str] = Field(None)
    nztr_license_number: Optional[str] = Field(None, description="NZTR trainer license number.")


class Trainer(TrainerCreate):
    """Full trainer record with server-generated fields."""
    id: str
    created_at: datetime
    updated_at: datetime


class TrainerUpdate(BaseModel):
    """Payload for updating a trainer record. All fields optional."""
    name: Optional[str] = None
    stable_name: Optional[str] = None
    location: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    nztr_license_number: Optional[str] = None


# ─── HLT ──────────────────────────────────────────────────────────────────────

class DocumentStatus(BaseModel):
    """Status of a generated legal document."""
    status: Literal["pending", "reviewed"] = "pending"
    gcs_url: Optional[str] = None


class HLTDocuments(BaseModel):
    """The three legal documents for an HLT."""
    term_sheet: DocumentStatus = Field(default_factory=DocumentStatus)
    pds: DocumentStatus = Field(default_factory=DocumentStatus)
    sa: DocumentStatus = Field(default_factory=DocumentStatus)


class HLTCreate(BaseModel):
    """Payload for creating a new HLT record."""
    horse_microchip: str = Field(
        ...,
        pattern=r"^\d{15}$",
        description="Reference to the horse by microchip.",
    )
    owner_id: str = Field(..., description="Reference to the owner document ID.")
    trainer_id: str = Field(..., description="Reference to the trainer document ID.")
    lease_period_months: int = Field(..., ge=1, examples=[36])
    lease_start_date: date = Field(...)
    leasehold_stake_percentage: float = Field(..., ge=0, le=100)
    investor_return_percentage: float = Field(..., ge=0, le=100)
    syndicate_price_cents: int = Field(..., ge=0, examples=[500000])
    shares_total: int = Field(..., ge=1, examples=[50])
    shares_sold: int = Field(0, ge=0, description="Step 1: always 0.")
    share_price_cents: int = Field(..., ge=0, examples=[10000])
    fractional_interest_per_share: Optional[float] = Field(None)
    currency: Literal["NZD"] = Field("NZD")


class HLT(HLTCreate):
    """Full HLT record with server-generated fields."""
    id: str
    status: Literal["draft", "reviewed", "publish_ready", "published"] = "draft"
    documents: HLTDocuments = Field(default_factory=HLTDocuments)
    created_at: datetime
    updated_at: datetime


class HLTUpdate(BaseModel):
    """Payload for updating an HLT record. All fields optional."""
    lease_period_months: Optional[int] = None
    lease_start_date: Optional[date] = None
    leasehold_stake_percentage: Optional[float] = None
    investor_return_percentage: Optional[float] = None
    syndicate_price_cents: Optional[int] = None
    shares_total: Optional[int] = None
    share_price_cents: Optional[int] = None
    fractional_interest_per_share: Optional[float] = None
    status: Optional[Literal["draft", "reviewed", "publish_ready", "published"]] = None


# ─── Asset ─────────────────────────────────────────────────────────────────────

class AssetCreate(BaseModel):
    """Payload for creating asset metadata (upload creates the file first)."""
    entity_type: Literal["horse", "owner", "trainer", "hlt", "marketplace"]
    entity_id: str = Field(..., description="For horses, this is the microchip number.")
    asset_type: Literal["image", "document"]
    file_name: str
    mime_type: str
    file_size_bytes: int
    alt: Optional[str] = None
    tags: list[str] = Field(default_factory=list)
    is_primary: bool = False
    gcs_url: str
    public_url: Optional[str] = None
    thumbnail_url: Optional[str] = None
    uploaded_by: str


class Asset(AssetCreate):
    """Full asset record with server-generated fields."""
    id: str
    created_at: datetime


# ─── Content ──────────────────────────────────────────────────────────────────

class ContentSegment(BaseModel):
    """A single segment of transcribed speech with speaker attribution."""
    start_time: float = Field(..., description="Start time in seconds.")
    end_time: float = Field(..., description="End time in seconds.")
    speaker: str = Field(..., description="Speaker name (e.g. 'Andrew Scott').")
    text: str = Field(..., description="Transcribed text for this segment.")


class ContentSpeaker(BaseModel):
    """Speaker identity mapping."""
    name: str = Field(..., description="Real name (e.g. 'Andrew Scott').")
    label: str = Field(..., description="Diarization label (e.g. 'spk0').")


class ContentCreate(BaseModel):
    """Payload for creating a content record (transcript, video update, etc.)."""
    content_type: Literal["transcript", "video_update", "race_report", "workout_update", "general_update"] = Field(
        ..., description="Content type."
    )
    horse_microchip: str = Field(
        ...,
        pattern=r"^\d{15}$",
        description="Reference to the horse by microchip.",
    )
    title: str = Field(..., description="Content title (e.g. email subject).")
    content_date: date = Field(..., description="Date of the content (from email or recording).")
    speakers: list[ContentSpeaker] = Field(
        default_factory=list,
        description="Speaker identity mappings.",
    )
    full_text: str = Field(..., description="Full concatenated transcript text.")
    segments: list[ContentSegment] = Field(
        default_factory=list,
        description="Timestamped transcript segments with speaker attribution.",
    )
    source: str = Field(
        ...,
        description="Source of the transcript (e.g. 'google_speech_v1').",
    )
    source_email_id: Optional[str] = Field(
        None,
        description="Gmail message ID for deduplication.",
    )
    asset_ids: list[str] = Field(
        default_factory=list,
        description="Linked GCS asset IDs (video, audio files).",
    )
    status: Literal["draft", "published"] = Field("draft")


class Content(ContentCreate):
    """Full content record with server-generated fields."""
    id: str
    created_at: datetime
    updated_at: datetime


class ContentUpdate(BaseModel):
    """Payload for updating a content record. All fields optional."""
    content_type: Optional[Literal["transcript", "video_update", "race_report", "workout_update", "general_update"]] = None
    title: Optional[str] = None
    content_date: Optional[date] = None
    speakers: Optional[list[ContentSpeaker]] = None
    full_text: Optional[str] = None
    segments: Optional[list[ContentSegment]] = None
    source: Optional[str] = None
    asset_ids: Optional[list[str]] = None
    status: Optional[Literal["draft", "published"]] = None


# ─── Holding (Digital Ledger) ──────────────────────────────────────────────────

class HoldingCreate(BaseModel):
    """Payload for creating a new holding (ownership record)."""
    user_id: str = Field(..., description="Firebase Auth UID of the investor.")
    hlt_id: str = Field(..., description="Reference to the HLT campaign document ID.")
    horse_microchip: str = Field(..., pattern=r"^\d{15}$", description="Reference to the horse by microchip.")
    shares_owned: int = Field(..., ge=1, description="Number of shares owned.")
    percentage_owned: float = Field(..., ge=0.0, le=100.0, description="Percentage of ownership.")
    purchase_price_cents: int = Field(..., ge=0, description="Purchase price in cents.")
    stripe_session_id: str = Field(..., description="Stripe Checkout Session ID.")
    document_acknowledgements: dict[str, bool] = Field(
        default_factory=dict,
        description="Records user's check of PDS, Term Sheet, and SA."
    )


class Holding(HoldingCreate):
    """Full holding record with server-generated fields."""
    id: str = Field(..., description="Firestore document ID")
    status: Literal["pending", "paid", "refunded"] = Field("pending")
    created_at: datetime
    updated_at: datetime


# ─── GoverningBody ─────────────────────────────────────────────────────────────

class GoverningBodyCreate(BaseModel):
    """Payload for creating a governing body record."""
    governing_body_code: str = Field(
        ...,
        examples=["NZTR"],
        description="Short canonical code used as the Firestore document ID.",
    )
    governing_body_name: str = Field(..., examples=["New Zealand Thoroughbred Racing"])
    website: Optional[str] = Field(None)
    status: Literal["active", "inactive"] = Field("active")
    notes: Optional[str] = Field(None)


class GoverningBody(GoverningBodyCreate):
    """Full governing body record with server-generated fields."""
    id: str
    created_at: datetime
    updated_at: datetime


class GoverningBodyUpdate(BaseModel):
    """Payload for updating a governing body record. All fields optional."""
    governing_body_code: Optional[str] = None
    governing_body_name: Optional[str] = None
    website: Optional[str] = None
    status: Optional[Literal["active", "inactive"]] = None
    notes: Optional[str] = None


# ─── Loveracing.nz Reference ──────────────────────────────────────────────────

# NOTE: LoveracingRef, RaceResult, HorseRacingSummary moved to 05_industry-data/src/models.py