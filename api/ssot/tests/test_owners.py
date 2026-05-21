"""Tests for the SSOT Owners API."""

import pytest
from pydantic import ValidationError

from models import OwnerCreate, OwnerUpdate


class TestOwnerCreate:
    """Test OwnerCreate Pydantic model validation."""

    def test_valid_individual_owner(self):
        owner = OwnerCreate(
            name="John Smith",
            email="john@example.com",
            phone="+64211234567",
            type="individual",
        )
        assert owner.name == "John Smith"
        assert owner.type == "individual"

    def test_valid_syndicate_owner(self):
        owner = OwnerCreate(
            name="Racing Syndicate NZ",
            email="syndicate@example.com",
            phone="+64219876543",
            type="syndicate",
        )
        assert owner.type == "syndicate"

    def test_valid_corporate_owner(self):
        owner = OwnerCreate(
            name="Evolution Stables Ltd",
            email="info@evolution.nz",
            phone="+6491234567",
            type="corporate",
        )
        assert owner.type == "corporate"

    def test_type_must_be_valid(self):
        with pytest.raises(ValidationError):
            OwnerCreate(
                name="Test",
                email="test@example.com",
                phone="+64211234567",
                type="invalid",
            )

    def test_email_required(self):
        with pytest.raises(ValidationError):
            OwnerCreate(
                name="Test",
                phone="+64211234567",
                type="individual",
            )


class TestOwnerUpdate:
    """Test OwnerUpdate allows partial updates."""

    def test_partial_update(self):
        update = OwnerUpdate(name="Updated Name")
        assert update.name == "Updated Name"
        assert update.email is None
        assert update.phone is None

    def test_all_fields_optional(self):
        update = OwnerUpdate()
        assert update.name is None
        assert update.email is None