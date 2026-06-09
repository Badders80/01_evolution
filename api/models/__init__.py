"""
Evolution API — Shared Pydantic Models

These models are the single source of truth for data validation.
They mirror the JSON Schemas in dna/schemas/ exactly.
Every Cloud Function imports from this package.
"""

from datetime import date, datetime
from typing import Literal, Optional
from pydantic import BaseModel, Field, field_validator, model_validator
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
    breeding_url: Optional[str] = Field(None, description="loveracing.nz breeding page URL")
    performance_profile_url: Optional[str] = Field(None, description="loveracing.nz performance modal URL")
    country_code: Optional[str] = Field("NZ")
    nztr_life_number: Optional[str] = Field(
        None,
        pattern=r"^NZ\d{8}$",
        description="NZTR life number. e.g. NZ00427416",
    )
    horse_status: Literal["active", "retired", "deceased", "sold", "transferred"] = Field("active")
    identity_status: Literal["verified", "pending", "unverified"] = Field("pending")
    source_primary: Optional[str] = Field(None, description="e.g. loveracing.nz")
    source_last_verified_at: Optional[date] = Field(None)


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
    breeding_url: Optional[str] = None
    performance_profile_url: Optional[str] = None
    country_code: Optional[str] = None
    nztr_life_number: Optional[str] = None
    horse_status: Optional[Literal["active", "retired", "deceased", "sold", "transferred"]] = None
    identity_status: Optional[Literal["verified", "pending", "unverified"]] = None
    source_primary: Optional[str] = None
    source_last_verified_at: Optional[date] = None


# ─── Owner ────────────────────────────────────────────────────────────────────

class OwnerCreate(BaseModel):
    """Payload for creating a new owner record."""
    name: str = Field(..., description="Full legal name.", examples=["Golden Eye Trust"])
    email: str = Field(..., description="Primary contact email.")
    phone: Optional[str] = Field(None, examples=["+64 21 123 4567"])
    type: Literal["individual", "syndicate", "corporate"] = Field("individual")
    entity_type: Literal["individual", "company", "syndicate"] = Field("individual")
    contact_name: Optional[str] = Field(None)
    website: Optional[str] = Field(None)
    x_url: Optional[str] = Field(None)
    instagram_url: Optional[str] = Field(None)
    facebook_url: Optional[str] = Field(None)
    profile_status: Literal["active", "inactive", "under_review"] = Field("active")
    profile_origin: Optional[str] = Field(None)
    notes: Optional[str] = Field(None)
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
    entity_type: Optional[Literal["individual", "company", "syndicate"]] = None
    contact_name: Optional[str] = None
    website: Optional[str] = None
    x_url: Optional[str] = None
    instagram_url: Optional[str] = None
    facebook_url: Optional[str] = None
    profile_status: Optional[Literal["active", "inactive", "under_review"]] = None
    profile_origin: Optional[str] = None
    notes: Optional[str] = None
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
    full_address: Optional[str] = Field(None)
    bio: Optional[str] = Field(None)
    notable_wins: list[str] = Field(default_factory=list)
    website: Optional[str] = Field(None)
    x_url: Optional[str] = Field(None)
    instagram_url: Optional[str] = Field(None)
    facebook_url: Optional[str] = Field(None)
    profile_status: Literal["active", "inactive", "under_review"] = Field("active")
    contact_name: Optional[str] = Field(None)


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
    full_address: Optional[str] = None
    bio: Optional[str] = None
    notable_wins: Optional[list[str]] = None
    website: Optional[str] = None
    x_url: Optional[str] = None
    instagram_url: Optional[str] = None
    facebook_url: Optional[str] = None
    profile_status: Optional[Literal["active", "inactive", "under_review"]] = None
    contact_name: Optional[str] = None


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
    """Payload for creating a new HLT record (lean published record)."""
    horse_microchip: str = Field(
        ...,
        pattern=r"^\d{15}$",
        description="Reference to the horse by microchip.",
    )
    owner_id: str = Field(..., description="Reference to the owner document ID.")
    trainer_id: str = Field(..., description="Reference to the trainer document ID.")
    lease_id: str = Field(..., description="Reference to the lease document ID (canonical).")
    status: Literal["draft", "reviewed", "publish_ready", "published"] = "draft"


class HLT(HLTCreate):
    """Full HLT record with server-generated fields."""
    id: str
    status: Literal["draft", "reviewed", "publish_ready", "published"] = "draft"
    documents: HLTDocuments = Field(default_factory=HLTDocuments)
    created_at: datetime
    updated_at: datetime


class HLTUpdate(BaseModel):
    """Payload for updating an HLT record. All fields optional."""
    lease_id: Optional[str] = None
    status: Optional[Literal["draft", "reviewed", "publish_ready", "published"]] = None


# ─── Lease ────────────────────────────────────────────────────────────────────

class LeaseCreate(BaseModel):
    """Payload for creating a new lease record with auto-calculated pricing.

    Core inputs: percentage_leased + duration_months + min_unit_size.
    Pricing inputs: price_basis + price_period + price_amount.
    System derives all other commercial fields.
    """
    # ─── Identity ─────────────────────────────────────
    lease_id: str = Field(..., description="Canonical lease ID. e.g. LSE-001")
    horse_id: str = Field(..., description="Reference to horse microchip or canonical ID.")

    # ─── Term ─────────────────────────────────────────
    start_date: date = Field(...)
    end_date: date = Field(...)
    duration_months: int = Field(..., ge=1)

    # ─── Stake ────────────────────────────────────────
    percent_leased: float = Field(..., ge=0, le=100, description="Total % of horse being leased. e.g. 5, 10")
    token_count: int = Field(..., ge=1, description="Number of tokens issued.")
    min_unit_size: float = Field(
        ..., gt=0, le=100,
        description="Minimum purchasable unit (%). e.g. 0.25, 0.50. Must divide evenly into percent_leased."
    )

    # ─── Pricing (3 inputs → derive rest) ─────────────
    price_basis: Literal["per_1pct", "full_stake"] = Field(
        ..., description="per_1pct = price is per 1%. full_stake = price is for the whole percent_leased stake."
    )
    price_period: Literal["month", "year", "total"] = Field(
        ..., description="Is the price_amount per month, per year, or for the total duration?"
    )
    price_amount: float = Field(..., ge=0, description="Dollar amount matching basis + period.")

    # ─── Split ────────────────────────────────────────
    investor_share_percent: float = Field(..., ge=0, le=100)
    owner_share_percent: float = Field(..., ge=0, le=100)
    platform_fee_percent: float = Field(0, ge=0)

    # ─── Status ───────────────────────────────────────
    lease_status: Literal["draft", "review", "complete"] = "draft"

    # ─── Derived (auto-populated) ─────────────────────
    price_per_1pct_per_month: float = Field(0, ge=0, description="Canonical unit. All other prices derive from this.")
    price_per_1pct_per_year: float = Field(0, ge=0)
    monthly_stake_price: float = Field(0, ge=0, description="price_per_1pct_per_month × percent_leased")
    annual_stake_price: float = Field(0, ge=0, description="price_per_1pct_per_year × percent_leased")
    total_issuance_value_nzd: float = Field(0, ge=0, description="Full value for the lease duration.")
    percent_per_token: float = Field(0, ge=0, description="percent_leased ÷ token_count")
    token_price_nzd: float = Field(0, ge=0, description="total_issuance_value_nzd ÷ token_count")

    @model_validator(mode="after")
    def compute_prices(self):
        """Derive canonical price_per_1pct_per_month from the 3 pricing inputs,
        then populate all other derived fields."""
        pct = self.percent_leased
        months = self.duration_months
        amount = self.price_amount
        basis = self.price_basis
        period = self.price_period

        # Step 1: Compute price_per_1pct_per_month
        if basis == "per_1pct":
            if period == "month":
                self.price_per_1pct_per_month = amount
            elif period == "year":
                self.price_per_1pct_per_month = amount / 12.0
            elif period == "total":
                self.price_per_1pct_per_month = amount / months
        elif basis == "full_stake":
            if period == "month":
                self.price_per_1pct_per_month = amount / pct
            elif period == "year":
                self.price_per_1pct_per_month = (amount / 12.0) / pct
            elif period == "total":
                self.price_per_1pct_per_month = (amount / months) / pct

        # Step 2: Derive all other fields
        self.price_per_1pct_per_year = self.price_per_1pct_per_month * 12.0
        self.monthly_stake_price = self.price_per_1pct_per_month * pct
        self.annual_stake_price = self.price_per_1pct_per_year * pct
        self.total_issuance_value_nzd = self.price_per_1pct_per_month * months * pct
        self.percent_per_token = pct / self.token_count
        self.token_price_nzd = self.total_issuance_value_nzd / self.token_count

        return self

    @model_validator(mode="after")
    def check_splits(self):
        """Investor + owner + platform must equal 100%."""
        total = self.investor_share_percent + self.owner_share_percent + self.platform_fee_percent
        if abs(total - 100.0) > 0.01:
            raise ValueError(
                f"Share split must sum to 100%. Got investor={self.investor_share_percent}, "
                f"owner={self.owner_share_percent}, platform={self.platform_fee_percent} = {total}"
            )
        return self

    @model_validator(mode="after")
    def check_unit_divisibility(self):
        """percent_leased must divide evenly by min_unit_size (no fractional cents allowed)."""
        if self.min_unit_size <= 0:
            raise ValueError("min_unit_size must be > 0")
        remainder = self.percent_leased % self.min_unit_size
        if abs(remainder) > 1e-9:
            raise ValueError(
                f"percent_leased ({self.percent_leased}) must be evenly divisible by "
                f"min_unit_size ({self.min_unit_size}). Remainder: {remainder}"
            )
        return self


class Lease(LeaseCreate):
    """Full lease record with server-generated fields."""
    id: str
    created_at: datetime
    updated_at: datetime


class LeaseUpdate(BaseModel):
    """Payload for updating a lease record. Only core/pricing inputs allowed.
    Derived fields are auto-recalculated by the system."""
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    duration_months: Optional[int] = None
    percent_leased: Optional[float] = None
    token_count: Optional[int] = None
    min_unit_size: Optional[float] = None
    price_basis: Optional[Literal["per_1pct", "full_stake"]] = None
    price_period: Optional[Literal["month", "year", "total"]] = None
    price_amount: Optional[float] = None
    investor_share_percent: Optional[float] = None
    owner_share_percent: Optional[float] = None
    platform_fee_percent: Optional[float] = None
    lease_status: Optional[Literal["draft", "review", "complete"]] = None


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


# ─── Loveracing.nz Reference ──────────────────────────────────────────────────

# NOTE: LoveracingRef, RaceResult, HorseRacingSummary moved to 05_industry-data/src/models.py
# Import from there if needed; kept for backward compat during transition.


# ─── DocumentRecord ───────────────────────────────────────────────────────────

DocReviewStatus = Literal["draft", "review", "approved", "rejected"]
SectionReviewStatus = Literal["pending", "approved", "rejected", "needs_revision"]


class ReviewSection(BaseModel):
    """A single document section with review status and reviewer notes."""
    section_name: str = Field(..., description="Canonical section identifier.")
    status: SectionReviewStatus = Field("pending")
    reviewer_notes: Optional[str] = Field(None)


class DocumentRecordCreate(BaseModel):
    """Payload for creating a document tracking record."""
    document_id: str = Field(..., description="Canonical document ID. e.g. DOC-LSE-001-PDS")
    lease_id: str = Field(..., description="Reference to lease canonical ID.")
    horse_id: str = Field(..., description="Horse microchip number.")
    document_type: Literal["term-sheet", "pds", "sa"] = Field(...)
    document_version: int = Field(1, ge=1)
    document_date: date = Field(...)
    source_reference: Optional[str] = Field(None, description="External reference or template version.")
    file_path: str = Field(..., description="GCS URL or relative path to the generated file.")
    is_current: bool = Field(True)
    notes: Optional[str] = Field(None)
    doc_review_status: DocReviewStatus = Field("draft")
    sections: list[ReviewSection] = Field(default_factory=list)


class DocumentRecord(DocumentRecordCreate):
    """Full document record with server-generated fields."""
    id: str = Field(..., description="Firestore document ID")
    created_at: datetime
    updated_at: datetime


class DocumentRecordUpdate(BaseModel):
    """Payload for updating a document record."""
    document_version: Optional[int] = None
    document_date: Optional[date] = None
    source_reference: Optional[str] = None
    file_path: Optional[str] = None
    is_current: Optional[bool] = None
    notes: Optional[str] = None
    doc_review_status: Optional[DocReviewStatus] = None
    sections: Optional[list[ReviewSection]] = None


# ─── Standard Document Sections ───────────────────────────────────────────────

DOC_TYPE_SECTIONS: dict[str, list[str]] = {
    "term-sheet": ["horse_details", "lease_terms", "pricing", "parties"],
    "pds": ["overview", "horse_details", "lease_terms", "risks", "fees", "contact"],
    "sa": ["parties", "lease_conditions", "payment_terms", "termination", "governing_law"],
}


def build_default_sections(doc_type: str) -> list[ReviewSection]:
    """Return a list of ReviewSection objects for a given doc_type, all pending."""
    names = DOC_TYPE_SECTIONS.get(doc_type, [])
    return [ReviewSection(section_name=name, status="pending") for name in names]

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