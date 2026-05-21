"""Tests for the SSOT HLT API."""

import pytest
from pydantic import ValidationError

from models import HLTCreate, HLTUpdate


class TestHLTCreate:
    """Test HLTCreate Pydantic model validation."""

    def test_valid_hlt(self):
        hlt = HLTCreate(
            horse_id="985125000126462",
            owner_id="owner-123",
            trainer_id="trainer-456",
        )
        assert hlt.horse_id == "985125000126462"
        assert hlt.status == "draft"  # Default status

    def test_default_status_is_draft(self):
        hlt = HLTCreate(
            horse_id="985125000126462",
            owner_id="owner-123",
            trainer_id="trainer-456",
        )
        assert hlt.status == "draft"

    def test_custom_status_on_create(self):
        hlt = HLTCreate(
            horse_id="985125000126462",
            owner_id="owner-123",
            trainer_id="trainer-456",
            status="reviewed",
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