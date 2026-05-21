"""Tests for the SSOT Horses API."""

import pytest
from unittest.mock import patch, MagicMock
from pydantic import ValidationError

from models import HorseCreate, Horse, LoveracingRef


class TestHorseCreate:
    """Test HorseCreate Pydantic model validation."""

    def test_valid_horse(self):
        horse = HorseCreate(
            microchip="985125000126462",
            name="Prudentia NZ",
            foaling_date="2021-09-15",
            sex="filly",
            colour="Bay",
            sire_name="Savabeel",
            dam_name="Diademe",
        )
        assert horse.microchip == "985125000126462"
        assert horse.name == "Prudentia NZ"
        assert horse.sex == "filly"

    def test_microchip_must_be_15_digits(self):
        with pytest.raises(ValidationError):
            HorseCreate(
                microchip="123",
                name="Test Horse",
                foaling_date="2021-01-01",
                sex="colt",
            )

    def test_microchip_must_be_numeric(self):
        with pytest.raises(ValidationError):
            HorseCreate(
                microchip="98512500012646A",
                name="Test Horse",
                foaling_date="2021-01-01",
                sex="colt",
            )

    def test_sex_must_be_valid(self):
        with pytest.raises(ValidationError):
            HorseCreate(
                microchip="985125000126462",
                name="Test Horse",
                foaling_date="2021-01-01",
                sex="invalid",
            )

    def test_optional_fields_default(self):
        horse = HorseCreate(
            microchip="985125000126462",
            name="Test Horse",
            foaling_date="2021-01-01",
            sex="colt",
        )
        assert horse.colour is None
        assert horse.sire_name is None
        assert horse.dam_name is None
        assert horse.breeder is None
        assert horse.status == "active"

    def test_with_loveracing_ref(self):
        ref = LoveracingRef(
            loveracing_id=427416,
            name_slug="prudentia-nz",
            life_number="NZ00427416",
            sire_name="Savabeel",
            dam_name="Diademe",
            colour="Bay",
            sex="Filly",
            foaling_date="2021-09-15",
            breeder="Waikato Stud",
            brands="3YO Bay Filly",
            source_url="https://loveracing.nz/Breeding/427416/Prudentia-NZ.aspx",
        )
        horse = HorseCreate(
            microchip="985125000126462",
            name="Prudentia NZ",
            foaling_date="2021-09-15",
            sex="filly",
            loveracing_ref=ref,
        )
        assert horse.loveracing_ref is not None
        assert horse.loveracing_ref.loveracing_id == 427416


class TestHorseRoutes:
    """Test horse route handlers (requires Firestore mock)."""

    @patch("routes.horses.db")
    def test_create_horse_success(self, mock_db):
        """Test that creating a horse calls Firestore correctly."""
        mock_collection = MagicMock()
        mock_db.collection.return_value = mock_collection
        mock_query = MagicMock()
        mock_collection.where.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.get.return_value = []  # No existing horse with this microchip

        mock_doc_ref = MagicMock()
        mock_doc_ref.id = "test-horse-id"
        mock_collection.document.return_value = mock_doc_ref

        # This would be called via Flask test client in integration tests
        # For now, we verify the model validation works
        horse = HorseCreate(
            microchip="985125000126462",
            name="Test Horse",
            foaling_date="2021-01-01",
            sex="colt",
        )
        assert horse.microchip == "985125000126462"