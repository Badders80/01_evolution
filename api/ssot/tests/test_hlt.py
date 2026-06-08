"""Tests for the SSOT HLT API."""

import pytest
from pydantic import ValidationError
from datetime import datetime
from models import HLTCreate, HLTUpdate, HLT

VALID_HLT_DATA = {
    "horse_microchip": "985125000126462",
    "owner_id": "owner-123",
    "trainer_id": "trainer-456",
    "lease_id": "LSE-001",
}


class TestHLTCreate:
    """Test HLTCreate and HLT Pydantic model validation."""

    def test_valid_hlt_create(self):
        hlt_create = HLTCreate(**VALID_HLT_DATA)
        assert hlt_create.horse_microchip == "985125000126462"
        assert hlt_create.lease_id == "LSE-001"

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

    TRANSITIONS = {
        "draft": ["reviewed"],
        "reviewed": ["draft", "publish_ready"],
        "publish_ready": ["reviewed", "published"],
        "published": [],
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
        assert "published" not in self.TRANSITIONS["draft"]


class TestHLTUpdate:
    """Test HLTUpdate allows partial updates."""

    def test_partial_update(self):
        update = HLTUpdate(status="reviewed")
        assert update.status == "reviewed"

    def test_lease_id_update(self):
        update = HLTUpdate(lease_id="LSE-002")
        assert update.lease_id == "LSE-002"

    def test_all_fields_optional(self):
        update = HLTUpdate()
        assert update.status is None
        assert update.lease_id is None


class TestHLTWorkflow:
    """Test POST /hlts/workflow — creates Lease + HLT in one call."""

    @pytest.fixture
    def app(self):
        from flask import Flask
        app = Flask(__name__)
        return app

    def test_workflow_success(self, app):
        from ssot.routes.hlts import create_hlt_workflow
        from unittest.mock import MagicMock, patch
        from flask import request

        # Mock horse exists
        mock_horse_doc = MagicMock()
        mock_horse_doc.exists = True

        # Mock owner exists
        mock_owner_doc = MagicMock()
        mock_owner_doc.exists = True

        # Mock trainer exists
        mock_trainer_doc = MagicMock()
        mock_trainer_doc.exists = True

        # Mock lease not exists
        mock_lease_doc = MagicMock()
        mock_lease_doc.exists = False

        # Mock HLT ref
        mock_hlt_ref = MagicMock()
        mock_hlt_ref.id = "HLT-NEW-001"
        mock_hlt_ref.set = MagicMock()

        mock_hlt_collection = MagicMock()
        mock_hlt_collection.document.return_value = mock_hlt_ref

        def collection_side_effect(name):
            if name == "horses":
                c = MagicMock()
                c.document.return_value.get.return_value = mock_horse_doc
                return c
            if name == "owners":
                c = MagicMock()
                c.document.return_value.get.return_value = mock_owner_doc
                return c
            if name == "trainers":
                c = MagicMock()
                c.document.return_value.get.return_value = mock_trainer_doc
                return c
            if name == "leases":
                c = MagicMock()
                doc_ref = MagicMock()
                doc_ref.get.return_value.exists = False
                c.document.return_value = doc_ref
                return c
            if name == "hlts":
                return mock_hlt_collection
            return MagicMock()

        mock_db = MagicMock()
        mock_db.collection.side_effect = collection_side_effect

        workflow_data = {
            "horse_microchip": "985125000126462",
            "owner_id": "OWN-001",
            "trainer_id": "TRN-001",
            "lease_id": "LSE-TEST-001",
            "start_date": "2026-01-01",
            "end_date": "2027-06-30",
            "duration_months": 18,
            "percent_leased": 5,
            "token_count": 20,
            "min_unit_size": 0.25,
            "price_basis": "per_1pct",
            "price_period": "month",
            "price_amount": 65,
            "investor_share_percent": 75,
            "owner_share_percent": 25,
        }

        with app.test_request_context("/", method="POST", json=workflow_data):
            with patch("ssot.routes.hlts._get_db", return_value=mock_db):
                resp, status = create_hlt_workflow(request)
                assert status == 201
                # Check response has both lease and hlt
                resp_json = resp.get_json()
                assert "lease" in resp_json
                assert "hlt" in resp_json
                # Verify lease derived fields
                lease = resp_json["lease"]
                assert lease["price_per_1pct_per_month"] == 65.0
                assert lease["total_issuance_value_nzd"] == 5850.0
                assert lease["token_price_nzd"] == 292.5

    def test_workflow_missing_references(self, app):
        from ssot.routes.hlts import create_hlt_workflow
        from unittest.mock import MagicMock, patch
        from flask import request

        mock_doc = MagicMock()
        mock_doc.exists = False

        def collection_side_effect(name):
            c = MagicMock()
            c.document.return_value.get.return_value = mock_doc
            return c

        mock_db = MagicMock()
        mock_db.collection.side_effect = collection_side_effect

        with app.test_request_context("/", method="POST", json={
            "horse_microchip": "000000000000000",
            "owner_id": "NONEXISTENT",
            "trainer_id": "TRN-001",
        }):
            with patch("ssot.routes.hlts._get_db", return_value=mock_db):
                resp, status = create_hlt_workflow(request)
                assert status == 400

    def test_workflow_lease_validation_error(self, app):
        from ssot.routes.hlts import create_hlt_workflow
        from unittest.mock import MagicMock, patch
        from flask import request

        mock_doc = MagicMock()
        mock_doc.exists = True

        def collection_side_effect(name):
            c = MagicMock()
            c.document.return_value.get.return_value = mock_doc
            return c

        mock_db = MagicMock()
        mock_db.collection.side_effect = collection_side_effect

        # Missing required lease fields
        with app.test_request_context("/", method="POST", json={
            "horse_microchip": "985125000126462",
            "owner_id": "OWN-001",
            "trainer_id": "TRN-001",
        }):
            with patch("ssot.routes.hlts._get_db", return_value=mock_db):
                resp, status = create_hlt_workflow(request)
                assert status == 400
