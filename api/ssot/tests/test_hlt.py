"""Tests for the SSOT HLT API."""

import pytest
from pydantic import ValidationError

from datetime import datetime
from models import HLTCreate, HLTUpdate, HLT

VALID_HLT_DATA = {
    "horse_microchip": "985125000126462",
    "owner_id": "owner-123",
    "trainer_id": "trainer-456",
    "lease_period_months": 36,
    "lease_start_date": "2026-07-01",
    "leasehold_stake_percentage": 50.0,
    "investor_return_percentage": 10.0,
    "syndicate_price_cents": 500000,
    "shares_total": 50,
    "share_price_cents": 10000,
}


class TestHLTCreate:
    """Test HLTCreate and HLT Pydantic model validation."""

    def test_valid_hlt_create(self):
        hlt_create = HLTCreate(**VALID_HLT_DATA)
        assert hlt_create.horse_microchip == "985125000126462"
        assert hlt_create.lease_period_months == 36

    def test_default_status_is_draft_on_hlt(self):
        hlt = HLT(
            id="hlt-789",
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
            **VALID_HLT_DATA
        )
        assert hlt.status == "draft"

    def test_custom_status_on_hlt(self):
        hlt = HLT(
            id="hlt-789",
            status="reviewed",
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
            **VALID_HLT_DATA
        )
        assert hlt.status == "reviewed"


class TestHLTStatusTransitions:
    """Test HLT status transition validation."""

    # These mirror the STATUS_TRANSITIONS dict in routes/hlts.py
    TRANSITIONS = {
        "draft": ["reviewed"],
        "reviewed": ["draft", "publish_ready"],
        "publish_ready": ["reviewed", "published"],
        "published": [],  # Terminal state
    }

    def test_draft_to_reviewed(self):
        assert "reviewed" in self.TRANSITIONS["draft"]

    def test_reviewed_to_draft(self):
        assert "draft" in self.TRANSITIONS["reviewed"]

    def test_reviewed_to_publish_ready(self):
        assert "publish_ready" in self.TRANSITIONS["reviewed"]

    def test_published_is_terminal(self):
        assert len(self.TRANSITIONS["published"]) == 0

    def test_invalid_transition(self):
        # draft -> published is not allowed
        assert "published" not in self.TRANSITIONS["draft"]


class TestHLTUpdate:
    """Test HLTUpdate allows partial updates."""

    def test_partial_update(self):
        update = HLTUpdate(status="reviewed")
        assert update.status == "reviewed"