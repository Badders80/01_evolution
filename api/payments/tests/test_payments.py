"""Tests for the Payments API."""

import json
import os
import sys
import pytest
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


@pytest.fixture
def app():
    from flask import Flask
    app = Flask(__name__)
    return app


class TestCreateSession:

    def test_requires_post_method(self, app):
        from payments.routes.create_session import handle
        from flask import request
        with app.test_request_context("/", method="GET"):
            resp = handle(request)
            assert resp[1] == 405

    def test_requires_all_fields(self, app):
        from payments.routes.create_session import handle
        from flask import request
        with app.test_request_context("/", method="POST", json={"user_id": "u1"}):
            resp = handle(request)
            assert resp[1] == 400
            data = json.loads(resp[0].data)
            assert "Missing required fields" in data["error"]

    def test_shares_must_be_positive_integer(self, app):
        from payments.routes.create_session import handle
        from flask import request
        with app.test_request_context("/", method="POST", json={
            "user_id": "u1", "hlt_id": "hlt-1",
            "shares_to_buy": -1,
            "success_url": "https://ok.com", "cancel_url": "https://no.com",
        }):
            resp = handle(request)
            assert resp[1] == 400
            data = json.loads(resp[0].data)
            assert "positive integer" in data["error"]

    def test_shares_must_be_integer_not_string(self, app):
        from payments.routes.create_session import handle
        from flask import request
        with app.test_request_context("/", method="POST", json={
            "user_id": "u1", "hlt_id": "hlt-1",
            "shares_to_buy": "abc",
            "success_url": "https://ok.com", "cancel_url": "https://no.com",
        }):
            resp = handle(request)
            assert resp[1] == 400
            data = json.loads(resp[0].data)
            assert "integer" in data["error"]

    @patch("payments.routes.create_session._get_db")
    def test_requires_kyc_verification(self, mock_db, app):
        from payments.routes.create_session import handle
        from flask import request
        mock_user_ref = MagicMock()
        mock_user_doc = MagicMock()
        mock_user_doc.exists = True
        mock_user_doc.to_dict.return_value = {"kyc_status": "unverified"}
        mock_user_ref.get.return_value = mock_user_doc
        mock_db.return_value.collection.return_value.document.return_value = mock_user_ref

        with app.test_request_context("/", method="POST", json={
            "user_id": "u1", "hlt_id": "hlt-1",
            "shares_to_buy": 5,
            "success_url": "https://ok.com", "cancel_url": "https://no.com",
        }):
            resp = handle(request)
            assert resp[1] == 403
            data = json.loads(resp[0].data)
            assert "KYC" in data["error"]

    @patch("payments.routes.create_session.stripe.checkout.Session")
    @patch("payments.routes.create_session._get_db")
    def test_creates_checkout_session(self, mock_db, mock_stripe_session, app):
        from payments.routes.create_session import handle
        from flask import request

        # Mock user (KYC verified)
        mock_user_ref = MagicMock()
        mock_user_doc = MagicMock()
        mock_user_doc.exists = True
        mock_user_doc.to_dict.return_value = {"kyc_status": "verified"}
        mock_user_ref.get.return_value = mock_user_doc

        # Mock HLT (published, with valid price)
        mock_hlt_ref = MagicMock()
        mock_hlt_doc = MagicMock()
        mock_hlt_doc.exists = True
        mock_hlt_doc.to_dict.return_value = {
            "status": "published",
            "shares_total": 20,
            "shares_sold": 0,
            "share_price_cents": 28000,
            "horse_microchip": "985125000126462",
            "fractional_interest_per_share": 5.0,
        }
        mock_hlt_ref.get.return_value = mock_hlt_doc

        # Mock horse
        mock_horse_ref = MagicMock()
        mock_horse_doc = MagicMock()
        mock_horse_doc.exists = True
        mock_horse_doc.to_dict.return_value = {"name": "Test Horse"}
        mock_horse_ref.get.return_value = mock_horse_doc

        # document() receives just the doc ID, not the full path.
        # Use a dict keyed by doc ID to return the right mock.
        doc_mocks = {
            "u1": mock_user_ref,
            "hlt-1": mock_hlt_ref,
            "985125000126462": mock_horse_ref,
        }
        mock_db.return_value.collection.return_value.document.side_effect = lambda doc_id: doc_mocks.get(doc_id, MagicMock())

        mock_session = MagicMock()
        mock_session.id = "cs_test123"
        mock_session.url = "https://checkout.stripe.com/test"
        mock_stripe_session.create.return_value = mock_session

        with app.test_request_context("/", method="POST", json={
            "user_id": "u1", "hlt_id": "hlt-1",
            "shares_to_buy": 5,
            "success_url": "https://ok.com", "cancel_url": "https://no.com",
        }):
            resp = handle(request)
            assert resp[1] == 200
            data = json.loads(resp[0].data)
            assert data["session_id"] == "cs_test123"


class TestPaymentsWebhook:

    def test_requires_post_method(self, app):
        from payments.routes.webhook import handle
        from flask import request
        with app.test_request_context("/", method="GET"):
            resp = handle(request)
            assert resp[1] == 405

    def test_rejects_missing_signature(self, app):
        from payments.routes.webhook import handle
        from flask import request
        with app.test_request_context("/", method="POST", data="{}", content_type="application/json"):
            resp = handle(request)
            assert resp[1] == 400

    @patch("payments.routes.webhook.stripe.Webhook.construct_event")
    def test_ignores_non_checkout_events(self, mock_construct, app):
        from payments.routes.webhook import handle
        from flask import request
        mock_construct.return_value = {
            "type": "charge.succeeded",
            "data": {"object": {}},
        }
        with app.test_request_context(
            "/", method="POST", data=json.dumps({"type": "test"}),
            headers={"Stripe-Signature": "sig_test"}, content_type="application/json"
        ):
            resp = handle(request)
            assert resp[1] == 200
            data = json.loads(resp[0].data)
            assert data["received"] is True

    @patch("payments.routes.webhook.stripe.Webhook.construct_event")
    @patch("payments.routes.webhook._get_db")
    @patch("payments.routes.webhook.process_purchase_transaction")
    def test_checkout_completed_updates_holding(self, mock_txn, mock_db, mock_construct, app):
        from payments.routes.webhook import handle
        from flask import request

        mock_session = MagicMock()
        mock_session.id = "cs_test_abc"
        mock_session.get.return_value = {
            "user_id": "user-abc",
            "hlt_id": "hlt-1",
            "shares_to_buy": "5",
            "horse_microchip": "985125000126462",
            "percentage_owned": "25.0",
            "purchase_price_cents": "140000",
        }

        mock_construct.return_value = {
            "type": "checkout.session.completed",
            "data": {"object": mock_session},
        }

        with app.test_request_context(
            "/", method="POST", data=json.dumps({"type": "test"}),
            headers={"Stripe-Signature": "sig_test"}, content_type="application/json"
        ):
            resp = handle(request)
            assert resp[1] == 200
            data = json.loads(resp[0].data)
            assert data["received"] is True
