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
            phone="+642****4567",
            type="individual",
        )
        assert owner.name == "John Smith"
        assert owner.type == "individual"
        assert owner.entity_type == "individual"
        assert owner.profile_status == "active"

    def test_valid_syndicate_owner(self):
        owner = OwnerCreate(
            name="Racing Syndicate NZ",
            email="syndicate@example.com",
            phone="+642****6543",
            type="syndicate",
            entity_type="syndicate",
        )
        assert owner.type == "syndicate"
        assert owner.entity_type == "syndicate"

    def test_valid_corporate_owner(self):
        owner = OwnerCreate(
            name="Evolution Stables Ltd",
            email="info@evolution.nz",
            phone="+649****4567",
            type="corporate",
            entity_type="company",
        )
        assert owner.type == "corporate"
        assert owner.entity_type == "company"

    def test_type_must_be_valid(self):
        with pytest.raises(ValidationError):
            OwnerCreate(
                name="Test",
                email="test@example.com",
                phone="+642****4567",
                type="invalid",
            )

    def test_entity_type_must_be_valid(self):
        with pytest.raises(ValidationError):
            OwnerCreate(
                name="Test",
                email="test@example.com",
                entity_type="invalid",
            )

    def test_profile_status_must_be_valid(self):
        with pytest.raises(ValidationError):
            OwnerCreate(
                name="Test",
                email="test@example.com",
                profile_status="banned",
            )

    def test_email_required(self):
        with pytest.raises(ValidationError):
            OwnerCreate(
                name="Test",
                phone="+642****4567",
                type="individual",
            )

    def test_full_fields(self):
        owner = OwnerCreate(
            name="B.A.X Bloodstock",
            email="bax@example.com",
            phone="+64 21 557 045",
            type="corporate",
            entity_type="company",
            contact_name="Kylie Bax",
            website="https://www.baxltd.com",
            x_url="https://x.com/baxkylie",
            instagram_url="https://instagram.com/b.a.x_syndications",
            facebook_url="https://facebook.com/bloodstockachievingxcellence",
            profile_status="active",
            profile_origin="seed",
            notes="Trading as B.A.X Ltd",
        )
        assert owner.contact_name == "Kylie Bax"
        assert owner.website == "https://www.baxltd.com"
        assert owner.x_url == "https://x.com/baxkylie"
        assert owner.profile_origin == "seed"
        assert owner.notes == "Trading as B.A.X Ltd"


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

    def test_update_new_fields(self):
        update = OwnerUpdate(
            contact_name="New Contact",
            website="https://new.example.com",
            profile_status="under_review",
            notes="Updated notes",
        )
        assert update.contact_name == "New Contact"
        assert update.website == "https://new.example.com"
        assert update.profile_status == "under_review"
        assert update.notes == "Updated notes"


class TestOwnerRoutes:
    """Test owner route handlers with Firestore mocks."""

    @pytest.fixture
    def app(self):
        from flask import Flask
        app = Flask(__name__)
        return app

    def test_create_owner_success(self, app):
        from ssot.routes.owners import create_owner
        from unittest.mock import MagicMock, patch
        from flask import request

        mock_doc_ref = MagicMock()
        mock_doc_ref.id = "OWN-001"
        mock_collection = MagicMock()
        mock_collection.document.return_value = mock_doc_ref
        mock_db = MagicMock()
        mock_db.collection.return_value = mock_collection

        with app.test_request_context(
            "/", method="POST", json={
                "name": "B.A.X Bloodstock",
                "email": "bax@example.com",
                "entity_type": "company",
                "profile_status": "active",
            }
        ):
            with patch("ssot.routes.owners._get_db", return_value=mock_db):
                resp, status = create_owner(request)
                assert status == 201
                mock_doc_ref.set.assert_called_once()

    def test_get_owner_success(self, app):
        from ssot.routes.owners import get_owner
        from unittest.mock import MagicMock, patch

        mock_doc = MagicMock()
        mock_doc.exists = True
        mock_doc.to_dict.return_value = {"name": "B.A.X Bloodstock"}
        mock_doc_ref = MagicMock()
        mock_doc_ref.get.return_value = mock_doc
        mock_collection = MagicMock()
        mock_collection.document.return_value = mock_doc_ref
        mock_db = MagicMock()
        mock_db.collection.return_value = mock_collection

        with app.test_request_context("/", method="GET"):
            with patch("ssot.routes.owners._get_db", return_value=mock_db):
                resp, status = get_owner("OWN-001")
                assert status == 200
                mock_collection.document.assert_called_once_with("OWN-001")

    def test_get_owner_not_found(self, app):
        from ssot.routes.owners import get_owner
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
            with patch("ssot.routes.owners._get_db", return_value=mock_db):
                resp, status = get_owner("OWN-999")
                assert status == 404

    def test_update_owner_success(self, app):
        from ssot.routes.owners import update_owner
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

        with app.test_request_context("/", method="PATCH", json={"website": "https://new.example.com"}):
            with patch("ssot.routes.owners._get_db", return_value=mock_db):
                resp, status = update_owner("OWN-001", request)
                assert status == 200
                mock_collection.document.assert_called_once_with("OWN-001")
                mock_doc_ref.update.assert_called_once()

    def test_delete_owner_success(self, app):
        from ssot.routes.owners import delete_owner
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
            if name == "owners":
                return mock_collection
            if name == "hlts":
                return mock_hlt_collection
            return MagicMock()

        mock_db.collection.side_effect = collection_side_effect

        with app.test_request_context("/", method="DELETE"):
            with patch("ssot.routes.owners._get_db", return_value=mock_db):
                resp, status = delete_owner("OWN-001")
                assert status == 200
                mock_collection.document.assert_called_once_with("OWN-001")
                mock_doc_ref.delete.assert_called_once()

    def test_list_owners_with_entity_type_filter(self, app):
        from ssot.routes.owners import list_owners
        from unittest.mock import MagicMock, patch
        from flask import request

        mock_doc = MagicMock()
        mock_doc.to_dict.return_value = {"name": "B.A.X"}
        mock_query = MagicMock()
        mock_query.get.return_value = [mock_doc]
        mock_collection = MagicMock()
        mock_collection.where.return_value = mock_query
        mock_db = MagicMock()
        mock_db.collection.return_value = mock_collection

        with app.test_request_context("/?entity_type=company", method="GET"):
            with patch("ssot.routes.owners._get_db", return_value=mock_db):
                resp, status = list_owners(request)
                assert status == 200
                mock_collection.where.assert_called_once_with("entity_type", "==", "company")
