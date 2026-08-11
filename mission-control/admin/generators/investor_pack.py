"""Investor pack (PDS + SA) generator for Mission Control.

Builds a field payload from HLT + horse + lease + owner/trainer in SQLite,
then renders the combined DRAFT DOCX via admin.generators.pack_lib.
"""

from __future__ import annotations

import re
from datetime import date
from pathlib import Path
from typing import TYPE_CHECKING, Any, Optional

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

_MC_ROOT = Path(__file__).resolve().parents[2]
_MONOREPO = _MC_ROOT.parents[1]


def _pack_lib():
    """Lazy-import pack DOCX library (local to Mission Control)."""
    from admin.generators import pack_lib

    return pack_lib


def _slugify(name: str) -> str:
    s = re.sub(r"[^\w\s-]", "", (name or "").strip().lower())
    s = re.sub(r"[\s_]+", "-", s).strip("-")
    return s or "horse"


def payload_from_hlt(hlt_id: str, db: "Session") -> dict[str, Any]:
    """Assemble wizard-shaped payload from Mission Control entities."""
    from admin.db import (
        HLT as HLTORM,
        Lease as LeaseORM,
        Horse as HorseORM,
        Owner as OwnerORM,
        Trainer as TrainerORM,
    )

    hlt = db.query(HLTORM).filter_by(id=hlt_id).first()
    if not hlt:
        raise ValueError(f"HLT {hlt_id} not found")

    horse = db.query(HorseORM).filter_by(microchip=hlt.horse_microchip).first()
    lease = db.query(LeaseORM).filter_by(lease_id=hlt.lease_id).first()
    owner = db.query(OwnerORM).filter_by(id=hlt.owner_id).first()
    trainer = db.query(TrainerORM).filter_by(id=hlt.trainer_id).first()

    if not horse:
        raise ValueError(f"Horse {hlt.horse_microchip} not found for HLT {hlt_id}")
    if not lease:
        raise ValueError(f"Lease {hlt.lease_id} not found for HLT {hlt_id}")

    slug = horse.name_slug or _slugify(horse.name)
    stake = float(lease.percent_leased or 0)
    tokens = int(lease.token_count or 0)
    lot = float(lease.percent_per_token or 0) or (stake / tokens if tokens else 0)

    cover = horse.cover_image or ""
    # Absolute or monorepo-relative paths work better for embedding
    if cover and not cover.startswith("http") and not cover.startswith("/"):
        pass
    elif cover.startswith("/images/"):
        cover = str(_MONOREPO / "02_website" / "public" / cover.lstrip("/"))

    horse_payload = {
        "slug": slug,
        "display_name": horse.name or slug,
        "legal_name": horse.name or slug,
        "microchip": horse.microchip or "",
        "life_number": getattr(horse, "life_number", "") or (
            f"NZ{horse.loveracing_id}" if horse.loveracing_id else ""
        ),
        "sex": horse.sex or "",
        "colour": horse.colour or "",
        "foaling_date": horse.foaling_date or "",
        "sire_name": horse.sire_name or "",
        "dam_name": horse.dam_name or "",
        "breeder": horse.breeder or "",
        "trainer_name": (trainer.name if trainer else "") or "",
        "trainer_stable": (trainer.stable_name if trainer else "") or "",
        "trainer_location": (trainer.location if trainer else "") or "",
        "owner_name": (owner.name if owner else "") or "",
        "leasehold_stake_pct": stake,
        "shares_total": tokens,
        "lot_pct": lot,
        "lease_period_months": lease.duration_months or "",
        "lease_start_date": lease.start_date or "",
        "lease_end_date": lease.end_date or "",
        "price_per_share_nzd": lease.token_price_nzd,
        "investor_return_pct": lease.investor_share_percent or 75,
        "platform_fee_pct": lease.platform_fee_percent or 5,
        "owner_rate_per_1pct_month": lease.price_per_1pct_per_month,
        "about_horse": (getattr(horse, "story", None) or "").strip()
        or (horse.breeder and f"Bred by {horse.breeder}.")
        or "In training with Evolution Stables partner trainers.",
        "story": (getattr(horse, "story", None) or "").strip(),
        "race_schedule": (getattr(horse, "next_up", None) or "").strip()
        or "Updates via Evolution investor channels as the horse progresses.",
        "cover_image_url": cover or "",
        "breeding_url": horse.breeding_url or (
            f"https://loveracing.nz/Breeding/{horse.loveracing_id}"
            if horse.loveracing_id
            else ""
        ),
        "hlt_id": hlt_id,
        "lease_id": lease.lease_id,
    }

    lib = _pack_lib()
    attachments = []
    try:
        attachments = lib.list_attachments(slug)
    except Exception:
        attachments = []

    return {
        "horse": horse_payload,
        "investor": {},  # general syndicate pack (no personalised investor)
        "attachments": attachments,
        "document_date": date.today().isoformat(),
        "source": "mission-control",
        "hlt_id": hlt_id,
    }


def generate_investor_pack_docx(hlt_id: str, db: "Session") -> tuple[bytes, Path, dict]:
    """
    Generate combined PDS+SA DRAFT DOCX for an HLT.

    Returns (docx_bytes, saved_path, payload).
    """
    lib = _pack_lib()
    payload = payload_from_hlt(hlt_id, db)
    out_path = lib.build_docx(payload)
    if not isinstance(out_path, Path):
        out_path = Path(out_path)
    data = out_path.read_bytes()
    return data, out_path, payload
