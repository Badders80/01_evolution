"""Tests for the SSOT Lease API."""

import pytest
from pydantic import ValidationError
from datetime import date

from models import LeaseCreate, LeaseUpdate


class TestLeaseCreate:
    """Test LeaseCreate Pydantic model validation."""

    def test_valid_lease(self):
        lease = LeaseCreate(
            lease_id="LSE-001",
            horse_id="985125000126462",
            start_date="2025-07-01",
            end_date="2026-06-30",
            duration_months=12,
            percent_leased=10,
            token_count=20,
            percent_per_token=0.5,
            token_price_nzd=240,
            total_issuance_value_nzd=4800,
            investor_share_percent=80,
            owner_share_percent=20,
        )
        assert lease.lease_id == "LSE-001"
        assert lease.lease_status == "draft"

    def test_lease_status_must_be_valid(self):
        with pytest.raises(ValidationError):
            LeaseCreate(
                lease_id="LSE-001",
                horse_id="985125000126462",
                start_date="2025-07-01",
                end_date="2026-06-30",
                duration_months=12,
                percent_leased=10,
                token_count=20,
                percent_per_token=0.5,
                token_price_nzd=240,
                total_issuance_value_nzd=4800,
                investor_share_percent=80,
                owner_share_percent=20,
                lease_status="invalid",
            )

    def test_percent_leased_bounds(self):
        with pytest.raises(ValidationError):
            LeaseCreate(
                lease_id="LSE-001",
                horse_id="985125000126462",
                start_date="2025-07-01",
                end_date="2026-06-30",
                duration_months=12,
                percent_leased=110,  # Invalid
                token_count=20,
                percent_per_token=0.5,
                token_price_nzd=240,
                total_issuance_value_nzd=4800,
                investor_share_percent=80,
                owner_share_percent=20,
            )

    def test_defaults(self):
        lease = LeaseCreate(
            lease_id="LSE-001",
            horse_id="985125000126462",
            start_date="2025-07-01",
            end_date="2026-06-30",
            duration_months=12,
            percent_leased=10,
            token_count=20,
            percent_per_token=0.5,
            token_price_nzd=240,
            total_issuance_value_nzd=4800,
            investor_share_percent=80,
            owner_share_percent=20,
        )
        assert lease.platform_fee_percent == 0
        assert lease.lease_status == "draft"


class TestLeaseUpdate:
    """Test LeaseUpdate allows partial updates."""

    def test_partial_update(self):
        update = LeaseUpdate(lease_status="review")
        assert update.lease_status == "review"
        assert update.token_price_nzd is None

    def test_all_fields_optional(self):
        update = LeaseUpdate()
        assert update.lease_status is None
        assert update.percent_leased is None


class TestLeaseRoutes:
    """Test lease route handlers with Firestore mocks."""

    @pytest.fixture
    def app(self):
        from flask import Flask
        app = Flask(__name__)
        return app

    def test_create_lease_success(self, app):
        from ssot.routes.leases import create_lease
        from unittest.mock import MagicMock, patch
        from flask import request

        mock_doc_ref = MagicMock()
        mock_doc_ref.get.return_value.exists = False
        mock_collection = MagicMock()
        mock_collection.document.return_value = mock_doc_ref
        mock_db = MagicMock()
        mock_db.collection.return_value = mock_collection

        with app.test_request_context("/", method="POST", json={
            "lease_id": "LSE-001",
            "horse_id": "985125000126462",
            "start_date": "2025-07-01",
            "end_date": "2026-06-30",
            "duration_months": 12,
            "percent_leased": 10,
            "token_count": 20,
            "percent_per_token": 0.5,
            "token_price_nzd": 240,
            "total_issuance_value_nzd": 4800,
            "investor_share_percent": 80,
            "owner_share_percent": 20,
        }):
            with patch("ssot.routes.leases._get_db", return_value=mock_db):
                resp, status = create_lease(request)
                assert status == 201
                mock_collection.document.assert_called_once_with("LSE-001")
                mock_doc_ref.set.assert_called_once()

    def test_create_lease_duplicate(self, app):
        from ssot.routes.leases import create_lease
        from unittest.mock import MagicMock, patch
        from flask import request

        mock_doc_ref = MagicMock()
        mock_doc_ref.get.return_value.exists = True
        mock_collection = MagicMock()
        mock_collection.document.return_value = mock_doc_ref
        mock_db = MagicMock()
        mock_db.collection.return_value = mock_collection

        with app.test_request_context("/", method="POST", json={
            "lease_id": "LSE-001",
            "horse_id": "985125000126462",
            "start_date": "2025-07-01",
            "end_date": "2026-06-30",
            "duration_months": 12,
            "percent_leased": 10,
            "token_count": 20,
            "percent_per_token": 0.5,
            "token_price_nzd": 240,
            "total_issuance_value_nzd": 4800,
            "investor_share_percent": 80,
            "owner_share_percent": 20,
        }):
            with patch("ssot.routes.leases._get_db", return_value=mock_db):
                resp, status = create_lease(request)
                assert status == 409

    def test_get_lease_success(self, app):
        from ssot.routes.leases import get_lease
        from unittest.mock import MagicMock, patch

        mock_doc = MagicMock()
        mock_doc.exists = True
        mock_doc.to_dict.return_value = {"lease_id": "LSE-001"}
        mock_doc_ref = MagicMock()
        mock_doc_ref.get.return_value = mock_doc
        mock_collection = MagicMock()
        mock_collection.document.return_value = mock_doc_ref
        mock_db = MagicMock()
        mock_db.collection.return_value = mock_collection

        with app.test_request_context("/", method="GET"):
            with patch("ssot.routes.leases._get_db", return_value=mock_db):
                resp, status = get_lease("LSE-001")
                assert status == 200

    def test_delete_lease_blocked_by_hlt(self, app):
        from ssot.routes.leases import delete_lease
        from unittest.mock import MagicMock, patch

        mock_hlt = MagicMock()
        mock_hlt_collection = MagicMock()
        mock_hlt_collection.where.return_value.limit.return_value.get.return_value = [mock_hlt]
        mock_doc = MagicMock()
        mock_doc.exists = True
        mock_doc_ref = MagicMock()
        mock_doc_ref.get.return_value = mock_doc
        mock_collection = MagicMock()
        mock_collection.document.return_value = mock_doc_ref
        mock_db = MagicMock()

        def collection_side_effect(name):
            if name == "leases":
                return mock_collection
            if name == "hlts":
                return mock_hlt_collection
            return MagicMock()

        mock_db.collection.side_effect = collection_side_effect

        with app.test_request_context("/", method="DELETE"):
            with patch("ssot.routes.leases._get_db", return_value=mock_db):
                resp, status = delete_lease("LSE-001")
                assert status == 409
