"""Tests for the SSOT Lease Calculator model + API."""

import pytest
from pydantic import ValidationError
from datetime import date

from core.models import LeaseCreate, LeaseUpdate


class TestLeaseCreateCalculator:
    """Test the pricing calculator logic."""

    def test_prudentia_per_1pct_month(self):
        """Prudentia: 5% leased, 18 months, $65 per 1% per month."""
        lease = LeaseCreate(
            lease_id="LSE-002",
            horse_id="985125000126462",
            start_date="2026-01-01",
            end_date="2027-06-30",
            duration_months=18,
            percent_leased=5,
            token_count=20,
            min_unit_size=0.25,
            price_basis="per_1pct",
            price_period="month",
            price_amount=65,
            investor_share_percent=75,
            owner_share_percent=25,
        )
        assert lease.price_per_1pct_per_month == 65.0
        assert lease.price_per_1pct_per_year == 780.0
        assert lease.monthly_stake_price == 325.0
        assert lease.annual_stake_price == 3900.0
        assert lease.total_issuance_value_nzd == 5850.0
        assert lease.percent_per_token == 0.25
        assert lease.token_price_nzd == 292.5

    def test_hottathanafantasy_per_1pct_year(self):
        """Hottathanafantasy: 5% leased, 16 months, $840 per 1% per year."""
        lease = LeaseCreate(
            lease_id="LSE-003",
            horse_id="985125000139165",
            start_date="2025-03-01",
            end_date="2026-06-30",
            duration_months=16,
            percent_leased=5,
            token_count=20,
            min_unit_size=0.25,
            price_basis="per_1pct",
            price_period="year",
            price_amount=840,
            investor_share_percent=75,
            owner_share_percent=25,
        )
        assert lease.price_per_1pct_per_month == 70.0
        assert lease.total_issuance_value_nzd == 5600.0
        assert lease.percent_per_token == 0.25
        assert lease.token_price_nzd == 280.0

    def test_first_gear_full_stake_total(self):
        """First Gear: 10% leased, 12 months, $4,800 total for full stake."""
        lease = LeaseCreate(
            lease_id="LSE-001",
            horse_id="985125000126713",
            start_date="2025-07-01",
            end_date="2026-06-30",
            duration_months=12,
            percent_leased=10,
            token_count=20,
            min_unit_size=0.50,
            price_basis="full_stake",
            price_period="total",
            price_amount=4800,
            investor_share_percent=80,
            owner_share_percent=20,
        )
        assert lease.price_per_1pct_per_month == 40.0
        assert lease.total_issuance_value_nzd == 4800.0
        assert lease.percent_per_token == 0.5
        assert lease.token_price_nzd == 240.0

    def test_full_stake_month(self):
        """Full stake priced per month. 10% leased, $400/month for full stake."""
        lease = LeaseCreate(
            lease_id="LSE-TEST",
            horse_id="985125000126462",
            start_date="2025-07-01",
            end_date="2026-06-30",
            duration_months=12,
            percent_leased=10,
            token_count=20,
            min_unit_size=0.50,
            price_basis="full_stake",
            price_period="month",
            price_amount=400,
            investor_share_percent=80,
            owner_share_percent=20,
        )
        assert lease.price_per_1pct_per_month == 40.0
        assert lease.total_issuance_value_nzd == 4800.0

    def test_per_1pct_total(self):
        """Per 1% priced for total duration. 5% leased, 18 months, $5,850 per 1% for total."""
        lease = LeaseCreate(
            lease_id="LSE-TEST2",
            horse_id="985125000126462",
            start_date="2026-01-01",
            end_date="2027-06-30",
            duration_months=18,
            percent_leased=5,
            token_count=20,
            min_unit_size=0.25,
            price_basis="per_1pct",
            price_period="total",
            price_amount=5850,
            investor_share_percent=75,
            owner_share_percent=25,
        )
        assert lease.price_per_1pct_per_month == 325.0
        assert lease.total_issuance_value_nzd == 29250.0


class TestLeaseCreateValidation:
    """Test LeaseCreate model validation errors."""

    def test_invalid_lease_status(self):
        with pytest.raises(ValidationError):
            LeaseCreate(
                lease_id="LSE-001",
                horse_id="985125000126462",
                start_date="2025-07-01",
                end_date="2026-06-30",
                duration_months=12,
                percent_leased=10,
                token_count=20,
                min_unit_size=0.50,
                price_basis="per_1pct",
                price_period="month",
                price_amount=65,
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
                percent_leased=110,
                token_count=20,
                min_unit_size=0.50,
                price_basis="per_1pct",
                price_period="month",
                price_amount=65,
                investor_share_percent=80,
                owner_share_percent=20,
            )

    def test_share_split_must_sum_100(self):
        with pytest.raises(ValidationError, match="Share split must sum to 100%"):
            LeaseCreate(
                lease_id="LSE-001",
                horse_id="985125000126462",
                start_date="2025-07-01",
                end_date="2026-06-30",
                duration_months=12,
                percent_leased=10,
                token_count=20,
                min_unit_size=0.50,
                price_basis="per_1pct",
                price_period="month",
                price_amount=65,
                investor_share_percent=70,
                owner_share_percent=20,
                platform_fee_percent=5,
            )

    def test_unit_divisibility_fail(self):
        with pytest.raises(ValidationError, match="evenly divisible"):
            LeaseCreate(
                lease_id="LSE-001",
                horse_id="985125000126462",
                start_date="2025-07-01",
                end_date="2026-06-30",
                duration_months=12,
                percent_leased=10,
                token_count=20,
                min_unit_size=0.30,  # 10 / 0.30 = 33.33 — not even
                price_basis="per_1pct",
                price_period="month",
                price_amount=65,
                investor_share_percent=80,
                owner_share_percent=20,
            )

    def test_unit_divisibility_pass(self):
        """10 / 0.25 = 40 — even."""
        lease = LeaseCreate(
            lease_id="LSE-001",
            horse_id="985125000126462",
            start_date="2025-07-01",
            end_date="2026-06-30",
            duration_months=12,
            percent_leased=10,
            token_count=40,
            min_unit_size=0.25,
            price_basis="per_1pct",
            price_period="month",
            price_amount=65,
            investor_share_percent=80,
            owner_share_percent=20,
        )
        assert lease.percent_per_token == 0.25
        assert lease.token_price_nzd == 195.0

    def test_min_unit_size_zero(self):
        with pytest.raises(ValidationError, match="min_unit_size"):
            LeaseCreate(
                lease_id="LSE-001",
                horse_id="985125000126462",
                start_date="2025-07-01",
                end_date="2026-06-30",
                duration_months=12,
                percent_leased=10,
                token_count=20,
                min_unit_size=0,
                price_basis="per_1pct",
                price_period="month",
                price_amount=65,
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
            min_unit_size=0.50,
            price_basis="per_1pct",
            price_period="month",
            price_amount=65,
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
        assert update.price_amount is None

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
            "min_unit_size": 0.50,
            "price_basis": "per_1pct",
            "price_period": "month",
            "price_amount": 40,
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
            "min_unit_size": 0.50,
            "price_basis": "per_1pct",
            "price_period": "month",
            "price_amount": 40,
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
