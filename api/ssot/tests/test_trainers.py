"""Tests for the SSOT Trainers API."""

import pytest
from pydantic import ValidationError

from core.models import TrainerCreate, TrainerUpdate


class TestTrainerCreate:
    """Test TrainerCreate Pydantic model validation."""

    def test_valid_trainer_minimal(self):
        trainer = TrainerCreate(
            name="Sam Spratt",
            stable_name="Evolution Stables",
            location="Cambridge, NZ",
            email="sam@evolution.nz",
        )
        assert trainer.name == "Sam Spratt"
        assert trainer.profile_status == "active"
        assert trainer.notable_wins == []

    def test_profile_status_must_be_valid(self):
        with pytest.raises(ValidationError):
            TrainerCreate(
                name="Sam Spratt",
                stable_name="Evolution Stables",
                location="Cambridge, NZ",
                email="sam@evolution.nz",
                profile_status="banned",
            )

    def test_full_fields(self):
        trainer = TrainerCreate(
            name="Wexford Stables",
            stable_name="Wexford Stables",
            location="Matamata, New Zealand",
            email="info@wexfordstables.co.nz",
            phone="+64 7 888 1234",
            full_address="Wexford Stables, Matamata, Waikato, New Zealand",
            bio="One of NZ's most iconic racing operations.",
            notable_wins=["Gr.1 New Zealand Oaks", "Gr.1 Livamol Classic"],
            website="https://www.wexfordstables.co.nz",
            x_url="https://x.com/WexfordStables",
            instagram_url="https://instagram.com/wexford_stables",
            facebook_url="https://facebook.com/WexfordStables",
            profile_status="active",
            contact_name="Andrew Scott",
        )
        assert trainer.full_address == "Wexford Stables, Matamata, Waikato, New Zealand"
        assert trainer.bio == "One of NZ's most iconic racing operations."
        assert trainer.notable_wins == ["Gr.1 New Zealand Oaks", "Gr.1 Livamol Classic"]
        assert trainer.website == "https://www.wexfordstables.co.nz"
        assert trainer.x_url == "https://x.com/WexfordStables"
        assert trainer.contact_name == "Andrew Scott"

    def test_notable_wins_default(self):
        trainer = TrainerCreate(
            name="Stephen Gray",
            stable_name="Copper Belt Lodge",
            location="Cambridge, New Zealand",
            email="stephen@example.com",
        )
        assert trainer.notable_wins == []


class TestTrainerUpdate:
    """Test TrainerUpdate allows partial updates."""

    def test_partial_update(self):
        update = TrainerUpdate(stable_name="Updated Stable")
        assert update.stable_name == "Updated Stable"
        assert update.email is None

    def test_all_fields_optional(self):
        update = TrainerUpdate()
        assert update.name is None
        assert update.bio is None

    def test_update_new_fields(self):
        update = TrainerUpdate(
            bio="Updated bio",
            website="https://new.example.com",
            notable_wins=["Gr.1 Derby"],
            profile_status="inactive",
            contact_name="New Contact",
        )
        assert update.bio == "Updated bio"
        assert update.website == "https://new.example.com"
        assert update.notable_wins == ["Gr.1 Derby"]
        assert update.profile_status == "inactive"
        assert update.contact_name == "New Contact"


class TestTrainerRoutes:
    """Test trainer route handlers with Firestore mocks."""

    @pytest.fixture
    def app(self):
        from flask import Flask
        app = Flask(__name__)
        return app

    def test_create_trainer_success(self, app):
        from ssot.routes.trainers import create_trainer
        from unittest.mock import MagicMock, patch
        from flask import request

        mock_doc_ref = MagicMock()
        mock_doc_ref.id = "TRN-001"
        mock_collection = MagicMock()
        mock_collection.document.return_value = mock_doc_ref
        mock_db = MagicMock()
        mock_db.collection.return_value = mock_collection

        with app.test_request_context(
            "/", method="POST", json={
                "name": "Wexford Stables",
                "stable_name": "Wexford Stables",
                "location": "Matamata, NZ",
                "email": "info@wexfordstables.co.nz",
                "bio": "Iconic racing operation.",
                "profile_status": "active",
            }
        ):
            with patch("ssot.routes.trainers._get_db", return_value=mock_db):
                resp, status = create_trainer(request)
                assert status == 201
                mock_doc_ref.set.assert_called_once()

    def test_get_trainer_success(self, app):
        from ssot.routes.trainers import get_trainer
        from unittest.mock import MagicMock, patch

        mock_doc = MagicMock()
        mock_doc.exists = True
        mock_doc.to_dict.return_value = {"name": "Wexford Stables"}
        mock_doc_ref = MagicMock()
        mock_doc_ref.get.return_value = mock_doc
        mock_collection = MagicMock()
        mock_collection.document.return_value = mock_doc_ref
        mock_db = MagicMock()
        mock_db.collection.return_value = mock_collection

        with app.test_request_context("/", method="GET"):
            with patch("ssot.routes.trainers._get_db", return_value=mock_db):
                resp, status = get_trainer("TRN-001")
                assert status == 200
                mock_collection.document.assert_called_once_with("TRN-001")

    def test_get_trainer_not_found(self, app):
        from ssot.routes.trainers import get_trainer
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
            with patch("ssot.routes.trainers._get_db", return_value=mock_db):
                resp, status = get_trainer("TRN-999")
                assert status == 404

    def test_update_trainer_success(self, app):
        from ssot.routes.trainers import update_trainer
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

        with app.test_request_context("/", method="PATCH", json={"bio": "Updated bio"}):
            with patch("ssot.routes.trainers._get_db", return_value=mock_db):
                resp, status = update_trainer("TRN-001", request)
                assert status == 200
                mock_collection.document.assert_called_once_with("TRN-001")
                mock_doc_ref.update.assert_called_once()

    def test_delete_trainer_success(self, app):
        from ssot.routes.trainers import delete_trainer
        from unittest.mock import MagicMock, patch

        mock_horse_collection = MagicMock()
        mock_horse_collection.where.return_value.limit.return_value.get.return_value = []
        mock_doc = MagicMock()
        mock_doc.exists = True
        mock_doc_ref = MagicMock()
        mock_doc_ref.get.return_value = mock_doc
        mock_collection = MagicMock()
        mock_collection.document.return_value = mock_doc_ref
        mock_db = MagicMock()

        def collection_side_effect(name):
            if name == "trainers":
                return mock_collection
            if name == "horses":
                return mock_horse_collection
            return MagicMock()

        mock_db.collection.side_effect = collection_side_effect

        with app.test_request_context("/", method="DELETE"):
            with patch("ssot.routes.trainers._get_db", return_value=mock_db):
                resp, status = delete_trainer("TRN-001")
                assert status == 200
                mock_collection.document.assert_called_once_with("TRN-001")
                mock_doc_ref.delete.assert_called_once()

    def test_list_trainers_with_profile_status_filter(self, app):
        from ssot.routes.trainers import list_trainers
        from unittest.mock import MagicMock, patch
        from flask import request

        mock_doc = MagicMock()
        mock_doc.to_dict.return_value = {"name": "Wexford Stables"}
        mock_query = MagicMock()
        mock_query.get.return_value = [mock_doc]
        mock_collection = MagicMock()
        mock_collection.where.return_value = mock_query
        mock_db = MagicMock()
        mock_db.collection.return_value = mock_collection

        with app.test_request_context("/?profile_status=active", method="GET"):
            with patch("ssot.routes.trainers._get_db", return_value=mock_db):
                resp, status = list_trainers(request)
                assert status == 200
                mock_collection.where.assert_called_once_with("profile_status", "==", "active")
