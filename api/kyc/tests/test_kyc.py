"""Tests for the KYC API."""

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

    def test_requires_user_id(self, app):
        from kyc.routes.create_session import handle
        from flask import request
        with app.test_request_context("/", method="POST", json={}):
            resp = handle(request)
            assert resp[1] == 400
            data = json.loads(resp[0].data)
            assert "user_id" in data["error"]

    def test_requires_post_method(self, app):
        from kyc.routes.create_session import handle
        from flask import request
        with app.test_request_context("/", method="GET"):
            resp = handle(request)
            assert resp[1] == 405

    @patch("kyc.routes.create_session.stripe.identity.VerificationSession")
    @patch("kyc.routes.create_session._get_db")
    def test_creates_stripe_session(self, mock_db, mock_stripe_session, app):
        from kyc.routes.create_session import handle
        from flask import request
        mock_user_ref = MagicMock()
        mock_user_doc = MagicMock()
        mock_user_doc.exists = True
        mock_user_doc.to_dict.return_value = {"email": "test@example.com"}
        mock_user_ref.get.return_value = mock_user_doc
        mock_db.return_value.collection.return_value.document.return_value = mock_user_ref
        mock_session = MagicMock()
        mock_session.id = "vs_test123"
        mock_session.url = "https://verify.stripe.com/test"
        mock_session.status = "requires_input"
        mock_stripe_session.create.return_value = mock_session
        with app.test_request_context("/", method="POST", json={
            "user_id": "user-abc",
            "return_url": "https://example.com/verify",
        }):
            resp = handle(request)
            assert resp[1] == 200
            data = json.loads(resp[0].data)
            assert data["session_id"] == "vs_test123"

    @patch("kyc.routes.create_session.stripe.identity.VerificationSession")
    @patch("kyc.routes.create_session._get_db")
    def test_lazy_creates_user_document(self, mock_db, mock_stripe_session, app):
        from kyc.routes.create_session import handle
        from flask import request
        mock_user_ref = MagicMock()
        mock_user_doc = MagicMock()
        mock_user_doc.exists = False
        mock_user_ref.get.return_value = mock_user_doc
        mock_db.return_value.collection.return_value.document.return_value = mock_user_ref
        mock_session = MagicMock()
        mock_session.id = "vs_test456"
        mock_session.url = "https://verify.stripe.com/test2"
        mock_session.status = "requires_input"
        mock_stripe_session.create.return_value = mock_session
        with app.test_request_context("/", method="POST", json={
            "user_id": "new-user",
            "email": "new@example.com",
        }):
            resp = handle(request)
            assert resp[1] == 200
            mock_user_ref.set.assert_called_once()


class TestKYCWebhook:

    def test_requires_post_method(self, app):
        from kyc.routes.webhook import handle
        from flask import request
        with app.test_request_context("/", method="GET"):
            resp = handle(request)
            assert resp[1] == 405

    def test_rejects_missing_signature(self, app):
        from kyc.routes.webhook import handle
        from flask import request
        with app.test_request_context("/", method="POST", data="{}", content_type="application/json"):
            resp = handle(request)
            assert resp[1] == 400

    @patch("kyc.routes.webhook.stripe.Webhook.construct_event")
    @patch("kyc.routes.webhook._get_db")
    @patch("kyc.routes.webhook._set_claims")
    def test_verified_event_updates_firestore(self, mock_set_claims, mock_db, mock_construct, app):
        from kyc.routes.webhook import handle
        from flask import request
        mock_construct.return_value = {
            "type": "identity.verification_session.verified",
            "data": {"object": {"metadata": {"user_id": "user-abc"}}},
        }
        mock_user_ref = MagicMock()
        mock_db.return_value.collection.return_value.document.return_value = mock_user_ref
        with app.test_request_context(
            "/", method="POST", data=json.dumps({"type": "test"}),
            headers={"Stripe-Signature": "sig_test"}, content_type="application/json"
        ):
            resp = handle(request)
            assert resp[1] == 200
            call_args = mock_user_ref.update.call_args[0][0]
            assert call_args["kyc_status"] == "verified"
            mock_set_claims.assert_called_once_with("user-abc", "verified")

    @patch("kyc.routes.webhook.stripe.Webhook.construct_event")
    @patch("kyc.routes.webhook._get_db")
    @patch("kyc.routes.webhook._set_claims")
    def test_requires_input_event_updates_firestore(self, mock_set_claims, mock_db, mock_construct, app):
        from kyc.routes.webhook import handle
        from flask import request
        mock_construct.return_value = {
            "type": "identity.verification_session.requires_input",
            "data": {"object": {"metadata": {"user_id": "user-xyz"}}},
        }
        mock_user_ref = MagicMock()
        mock_db.return_value.collection.return_value.document.return_value = mock_user_ref
        with app.test_request_context(
            "/", method="POST", data=json.dumps({"type": "test"}),
            headers={"Stripe-Signature": "sig_test"}, content_type="application/json"
        ):
            resp = handle(request)
            assert resp[1] == 200
            call_args = mock_user_ref.update.call_args[0][0]
            assert call_args["kyc_status"] == "requires_input"
            mock_set_claims.assert_called_once_with("user-xyz", "requires_input")

    @patch("kyc.routes.webhook.stripe.Webhook.construct_event")
    @patch("kyc.routes.webhook._get_db")
    @patch("kyc.routes.webhook._set_claims")
    def test_canceled_event_updates_firestore(self, mock_set_claims, mock_db, mock_construct, app):
        from kyc.routes.webhook import handle
        from flask import request
        mock_construct.return_value = {
            "type": "identity.verification_session.canceled",
            "data": {"object": {"metadata": {"user_id": "user-cancel"}}},
        }
        mock_user_ref = MagicMock()
        mock_db.return_value.collection.return_value.document.return_value = mock_user_ref
        with app.test_request_context(
            "/", method="POST", data=json.dumps({"type": "test"}),
            headers={"Stripe-Signature": "sig_test"}, content_type="application/json"
        ):
            resp = handle(request)
            assert resp[1] == 200
            call_args = mock_user_ref.update.call_args[0][0]
            assert call_args["kyc_status"] == "canceled"
            mock_set_claims.assert_called_once_with("user-cancel", "canceled")

    @patch("kyc.routes.webhook.stripe.Webhook.construct_event")
    @patch("kyc.routes.webhook._get_db")
    @patch("kyc.routes.webhook._set_claims")
    def test_unhandled_event_type_is_acknowledged(self, mock_set_claims, mock_db, mock_construct, app):
        from kyc.routes.webhook import handle
        from flask import request
        mock_construct.return_value = {
            "type": "identity.verification_session.processing",
            "data": {"object": {"metadata": {}}},
        }
        with app.test_request_context(
            "/", method="POST", data=json.dumps({"type": "test"}),
            headers={"Stripe-Signature": "sig_test"}, content_type="application/json"
        ):
            resp = handle(request)
            assert resp[1] == 200
            mock_db.return_value.collection.assert_not_called()
