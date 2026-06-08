"""Tests for the SSOT Horses API."""

import pytest
from unittest.mock import patch, MagicMock
from pydantic import ValidationError

from models import HorseCreate, Horse


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


class TestHorseRoutes:
    """Test horse route handlers with Firestore mocks."""

    @pytest.fixture
    def app(self):
        from flask import Flask
        app = Flask(__name__)
        return app

    def test_create_horse_success(self, app):
        from ssot.routes.horses import create_horse
        from unittest.mock import MagicMock, patch
        from flask import request

        mock_doc_ref = MagicMock()
        mock_doc_ref.get.return_value.exists = False
        mock_collection = MagicMock()
        mock_collection.document.return_value = mock_doc_ref
        mock_db = MagicMock()
        mock_db.collection.return_value = mock_collection

        with app.test_request_context(
            "/", method="POST", json={
                "microchip": "985125000126462",
                "name": "Test Horse",
                "foaling_date": "2021-01-01",
                "sex": "colt",
            }
        ):
            with patch("ssot.routes.horses._get_db", return_value=mock_db):
                resp, status = create_horse(request)
                assert status == 201
                mock_collection.document.assert_called_once_with("985125000126462")
                mock_doc_ref.set.assert_called_once()

    def test_create_horse_duplicate(self, app):
        from ssot.routes.horses import create_horse
        from unittest.mock import MagicMock, patch
        from flask import request

        mock_doc_ref = MagicMock()
        mock_doc_ref.get.return_value.exists = True
        mock_collection = MagicMock()
        mock_collection.document.return_value = mock_doc_ref
        mock_db = MagicMock()
        mock_db.collection.return_value = mock_collection

        with app.test_request_context(
            "/", method="POST", json={
                "microchip": "985125000126462",
                "name": "Test Horse",
                "foaling_date": "2021-01-01",
                "sex": "colt",
            }
        ):
            with patch("ssot.routes.horses._get_db", return_value=mock_db):
                resp, status = create_horse(request)
                assert status == 409
                mock_collection.document.assert_called_once_with("985125000126462")

    def test_get_horse_success(self, app):
        from ssot.routes.horses import get_horse
        from unittest.mock import MagicMock, patch

        mock_doc = MagicMock()
        mock_doc.exists = True
        mock_doc.id = "985125000126462"
        mock_doc.to_dict.return_value = {"name": "Test Horse"}
        mock_doc_ref = MagicMock()
        mock_doc_ref.get.return_value = mock_doc
        mock_collection = MagicMock()
        mock_collection.document.return_value = mock_doc_ref
        mock_db = MagicMock()
        mock_db.collection.return_value = mock_collection

        with app.test_request_context("/", method="GET"):
            with patch("ssot.routes.horses._get_db", return_value=mock_db):
                resp, status = get_horse("985125000126462")
                assert status == 200
                mock_collection.document.assert_called_once_with("985125000126462")

    def test_get_horse_not_found(self, app):
        from ssot.routes.horses import get_horse
        from unittest.mock import MagicMock, patch

        mock_doc = MagicMock()
        mock_doc.exists = False
        mock_doc_ref = MagicMock()
        mock_doc_ref.get.return_value = mock_doc
        mock_collection = MagicMock()
        mock_collection.document.return_value = mock_doc_ref
        mock_db = MagicMock()
        mock_db.collection.return_value = mock_collection

        with app.test_request_context("/", method="GET"):
            with patch("ssot.routes.horses._get_db", return_value=mock_db):
                resp, status = get_horse("985125000126462")
                assert status == 404
                mock_collection.document.assert_called_once_with("985125000126462")

    def test_update_horse_success(self, app):
        from ssot.routes.horses import update_horse
        from unittest.mock import MagicMock, patch
        from flask import request

        mock_doc = MagicMock()
        mock_doc.exists = True
        mock_doc_ref = MagicMock()
        mock_doc_ref.get.return_value = mock_doc
        mock_collection = MagicMock()
        mock_collection.document.return_value = mock_doc_ref
        mock_db = MagicMock()
        mock_db.collection.return_value = mock_collection

        with app.test_request_context("/", method="PATCH", json={"name": "Updated Name"}):
            with patch("ssot.routes.horses._get_db", return_value=mock_db):
                resp, status = update_horse("985125000126462", request)
                assert status == 200
                mock_collection.document.assert_called_once_with("985125000126462")
                mock_doc_ref.update.assert_called_once()

    def test_update_horse_not_found(self, app):
        from ssot.routes.horses import update_horse
        from unittest.mock import MagicMock, patch
        from flask import request

        mock_doc = MagicMock()
        mock_doc.exists = False
        mock_doc_ref = MagicMock()
        mock_doc_ref.get.return_value = mock_doc
        mock_collection = MagicMock()
        mock_collection.document.return_value = mock_doc_ref
        mock_db = MagicMock()
        mock_db.collection.return_value = mock_collection

        with app.test_request_context("/", method="PATCH", json={"name": "Updated Name"}):
            with patch("ssot.routes.horses._get_db", return_value=mock_db):
                resp, status = update_horse("985125000126462", request)
                assert status == 404

    def test_delete_horse_success(self, app):
        from ssot.routes.horses import delete_horse
        from unittest.mock import MagicMock, patch

        mock_hlt_collection = MagicMock()
        mock_hlt_collection.where.return_value.limit.return_value.get.return_value = []
        mock_doc = MagicMock()
        mock_doc.exists = True
        mock_doc_ref = MagicMock()
        mock_doc_ref.get.return_value = mock_doc
        mock_collection = MagicMock()
        mock_collection.document.return_value = mock_doc_ref
        mock_db = MagicMock()

        def collection_side_effect(name):
            if name == "horses":
                return mock_collection
            if name == "hlts":
                return mock_hlt_collection
            return MagicMock()

        mock_db.collection.side_effect = collection_side_effect

        with app.test_request_context("/", method="DELETE"):
            with patch("ssot.routes.horses._get_db", return_value=mock_db):
                resp, status = delete_horse("985125000126462")
                assert status == 200
                mock_collection.document.assert_called_once_with("985125000126462")
                mock_doc_ref.delete.assert_called_once()

    def test_delete_horse_not_found(self, app):
        from ssot.routes.horses import delete_horse
        from unittest.mock import MagicMock, patch

        mock_hlt_collection = MagicMock()
        mock_hlt_collection.where.return_value.limit.return_value.get.return_value = []
        mock_doc = MagicMock()
        mock_doc.exists = False
        mock_doc_ref = MagicMock()
        mock_doc_ref.get.return_value = mock_doc
        mock_collection = MagicMock()
        mock_collection.document.return_value = mock_doc_ref
        mock_db = MagicMock()

        def collection_side_effect(name):
            if name == "horses":
                return mock_collection
            if name == "hlts":
                return mock_hlt_collection
            return MagicMock()

        mock_db.collection.side_effect = collection_side_effect

        with app.test_request_context("/", method="DELETE"):
            with patch("ssot.routes.horses._get_db", return_value=mock_db):
                resp, status = delete_horse("985125000126462")
                assert status == 404
                mock_collection.document.assert_called_once_with("985125000126462")