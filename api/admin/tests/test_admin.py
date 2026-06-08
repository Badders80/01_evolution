"""Minimal tests for admin_server + admin/db.py"""

import pytest
from admin_server import app
from admin.db import ENGINE, init_db, Horse, Owner, Trainer, Lease, HLT, Document
from sqlalchemy import inspect


@pytest.fixture
def client():
    app.config["TESTING"] = True
    with app.test_client() as c:
        yield c


class TestAdminServer:
    def test_health(self, client):
        r = client.get("/api/health")
        assert r.status_code == 200
        assert r.json["status"] == "ok"

    def test_index_serves_html(self, client):
        r = client.get("/")
        assert r.status_code == 200
        assert b"HLT Mission Control" in r.data

    def test_static_app_js(self, client):
        r = client.get("/app.js")
        assert r.status_code == 200
        assert b"hash routing" in r.data or b"render" in r.data


class TestAdminDb:
    def test_all_tables_exist(self):
        inspector = inspect(ENGINE)
        tables = inspector.get_table_names()
        assert "horses" in tables
        assert "owners" in tables
        assert "trainers" in tables
        assert "leases" in tables
        assert "hlts" in tables
        assert "documents" in tables

    def test_horse_columns(self):
        inspector = inspect(ENGINE)
        cols = {c["name"] for c in inspector.get_columns("horses")}
        assert "microchip" in cols
        assert "name" in cols
        assert "trainer_id" in cols

    def test_owner_columns(self):
        inspector = inspect(ENGINE)
        cols = {c["name"] for c in inspector.get_columns("owners")}
        assert "id" in cols
        assert "email" in cols
        assert "profile_status" in cols

    def test_trainer_columns(self):
        inspector = inspect(ENGINE)
        cols = {c["name"] for c in inspector.get_columns("trainers")}
        assert "id" in cols
        assert "stable_name" in cols

    def test_lease_columns(self):
        inspector = inspect(ENGINE)
        cols = {c["name"] for c in inspector.get_columns("leases")}
        assert "lease_id" in cols
        assert "price_per_1pct_per_month" in cols

    def test_hlt_columns(self):
        inspector = inspect(ENGINE)
        cols = {c["name"] for c in inspector.get_columns("hlts")}
        assert "id" in cols
        assert "term_sheet_status" in cols

    def test_document_columns(self):
        inspector = inspect(ENGINE)
        cols = {c["name"] for c in inspector.get_columns("documents")}
        assert "id" in cols
        assert "hlt_id" in cols
        assert "doc_type" in cols
