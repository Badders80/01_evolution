"""Tests for the SSOT GoverningBodies API."""

import pytest
from pydantic import ValidationError

from core.models import GoverningBodyCreate, GoverningBodyUpdate


class TestGoverningBodyCreate:
    """Test GoverningBodyCreate Pydantic model validation."""

    def test_valid_governing_body(self):
        body = GoverningBodyCreate(
            governing_body_code="NZTR",
            governing_body_name="New Zealand Thoroughbred Racing",
            website="https://www.nzracing.co.nz",
            status="active",
            notes="Primary governing body",
        )
        assert body.governing_body_code == "NZTR"
        assert body.governing_body_name == "New Zealand Thoroughbred Racing"
        assert body.status == "active"

    def test_defaults(self):
        body = GoverningBodyCreate(
            governing_body_code="NZTR",
            governing_body_name="New Zealand Thoroughbred Racing",
        )
        assert body.status == "active"
        assert body.website is None
        assert body.notes is None

    def test_status_must_be_valid(self):
        with pytest.raises(ValidationError):
            GoverningBodyCreate(
                governing_body_code="NZTR",
                governing_body_name="New Zealand Thoroughbred Racing",
                status="invalid",
            )


class TestGoverningBodyUpdate:
    """Test GoverningBodyUpdate allows partial updates."""

    def test_partial_update(self):
        update = GoverningBodyUpdate(governing_body_name="Updated Name")
        assert update.governing_body_name == "Updated Name"
        assert update.governing_body_code is None

    def test_all_fields_optional(self):
        update = GoverningBodyUpdate()
        assert update.governing_body_code is None
        assert update.governing_body_name is None


class TestGoverningBodyRoutes:
    """Test governing body route handlers with Firestore mocks."""

    @pytest.fixture
    def app(self):
        from flask import Flask
        app = Flask(__name__)
        return app

    def test_create_governing_body_success(self, app):
        from ssot.routes.governing_bodies import create_governing_body
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
                "governing_body_code": "NZTR",
                "governing_body_name": "New Zealand Thoroughbred Racing",
            }
        ):
            with patch("ssot.routes.governing_bodies._get_db", return_value=mock_db):
                resp, status = create_governing_body(request)
                assert status == 201
                mock_collection.document.assert_called_once_with("NZTR")
                mock_doc_ref.set.assert_called_once()

    def test_create_governing_body_duplicate(self, app):
        from ssot.routes.governing_bodies import create_governing_body
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
                "governing_body_code": "NZTR",
                "governing_body_name": "New Zealand Thoroughbred Racing",
            }
        ):
            with patch("ssot.routes.governing_bodies._get_db", return_value=mock_db):
                resp, status = create_governing_body(request)
                assert status == 409
                mock_collection.document.assert_called_once_with("NZTR")

    def test_get_governing_body_success(self, app):
        from ssot.routes.governing_bodies import get_governing_body
        from unittest.mock import MagicMock, patch

        mock_doc = MagicMock()
        mock_doc.exists = True
        mock_doc.to_dict.return_value = {"governing_body_code": "NZTR"}
        mock_doc_ref = MagicMock()
        mock_doc_ref.get.return_value = mock_doc
        mock_collection = MagicMock()
        mock_collection.document.return_value = mock_doc_ref
        mock_db = MagicMock()
        mock_db.collection.return_value = mock_collection

        with app.test_request_context("/", method="GET"):
            with patch("ssot.routes.governing_bodies._get_db", return_value=mock_db):
                resp, status = get_governing_body("NZTR")
                assert status == 200
                mock_collection.document.assert_called_once_with("NZTR")

    def test_get_governing_body_not_found(self, app):
        from ssot.routes.governing_bodies import get_governing_body
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
            with patch("ssot.routes.governing_bodies._get_db", return_value=mock_db):
                resp, status = get_governing_body("NZTR")
                assert status == 404

    def test_update_governing_body_success(self, app):
        from ssot.routes.governing_bodies import update_governing_body
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

        with app.test_request_context("/", method="PATCH", json={"governing_body_name": "Updated"}):
            with patch("ssot.routes.governing_bodies._get_db", return_value=mock_db):
                resp, status = update_governing_body("NZTR", request)
                assert status == 200
                mock_collection.document.assert_called_once_with("NZTR")
                mock_doc_ref.update.assert_called_once()

    def test_update_governing_body_not_found(self, app):
        from ssot.routes.governing_bodies import update_governing_body
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

        with app.test_request_context("/", method="PATCH", json={"governing_body_name": "Updated"}):
            with patch("ssot.routes.governing_bodies._get_db", return_value=mock_db):
                resp, status = update_governing_body("NZTR", request)
                assert status == 404

    def test_delete_governing_body_success(self, app):
        from ssot.routes.governing_bodies import delete_governing_body
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
            if name == "governing_bodies":
                return mock_collection
            if name == "hlts":
                return mock_hlt_collection
            return MagicMock()

        mock_db.collection.side_effect = collection_side_effect

        with app.test_request_context("/", method="DELETE"):
            with patch("ssot.routes.governing_bodies._get_db", return_value=mock_db):
                resp, status = delete_governing_body("NZTR")
                assert status == 200
                mock_collection.document.assert_called_once_with("NZTR")
                mock_doc_ref.delete.assert_called_once()

    def test_delete_governing_body_blocked_by_hlt(self, app):
        from ssot.routes.governing_bodies import delete_governing_body
        from unittest.mock import MagicMock, patch

        mock_hlt_collection = MagicMock()
        mock_hlt_collection.where.return_value.limit.return_value.get.return_value = [MagicMock()]
        mock_db = MagicMock()

        def collection_side_effect(name):
            if name == "hlts":
                return mock_hlt_collection
            return MagicMock()

        mock_db.collection.side_effect = collection_side_effect

        with app.test_request_context("/", method="DELETE"):
            with patch("ssot.routes.governing_bodies._get_db", return_value=mock_db):
                resp, status = delete_governing_body("NZTR")
                assert status == 409

    def test_list_governing_bodies(self, app):
        from ssot.routes.governing_bodies import list_governing_bodies
        from unittest.mock import MagicMock, patch
        from flask import request

        mock_doc = MagicMock()
        mock_doc.to_dict.return_value = {"governing_body_code": "NZTR"}
        mock_query = MagicMock()
        mock_query.get.return_value = [mock_doc]
        mock_collection = MagicMock()
        mock_collection.where.return_value = mock_query
        mock_db = MagicMock()
        mock_db.collection.return_value = mock_collection

        with app.test_request_context("/?status=active", method="GET"):
            with patch("ssot.routes.governing_bodies._get_db", return_value=mock_db):
                resp, status = list_governing_bodies(request)
                assert status == 200
                mock_collection.where.assert_called_once_with("status", "==", "active")
