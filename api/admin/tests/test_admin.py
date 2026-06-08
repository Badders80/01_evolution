"""Tests for admin_server CRUD endpoints + horse_lookup."""

import pytest
from admin_server import app
from admin.db import ENGINE, init_db, Horse, Owner, Trainer
from sqlalchemy import inspect


@pytest.fixture
def client():
    app.config["TESTING"] = True
    with app.test_client() as c:
        yield c


@pytest.fixture(autouse=True)
def clean_db():
    """Wipe all entity rows before each test so order doesn't matter."""
    from admin.db import SessionLocal
    from sqlalchemy import text
    db = SessionLocal()
    try:
        for tbl in ["documents", "hlts", "leases", "horses", "owners", "trainers"]:
            db.execute(text(f"DELETE FROM {tbl}"))
        db.commit()
    finally:
        db.close()


# ─── Health / Static ──────────────────────────────────────────────────────────

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


# ─── DB Schema ───────────────────────────────────────────────────────────────

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


# ─── Horse CRUD ────────────────────────────────────────────────────────────────

class TestHorseCrud:
    def test_list_horses_empty(self, client):
        r = client.get("/api/horses")
        assert r.status_code == 200
        assert r.json["success"] is True
        assert r.json["data"] == []

    def test_create_horse(self, client):
        payload = {
            "microchip": "985125000126462",
            "name": "Prudentia (NZ) 2021",
            "foaling_date": "2021-10-01",
            "sex": "filly",
            "colour": "Bay",
            "sire_name": "PROISIR (AUS) 2009",
            "dam_name": "LITTLE BIT IRISH (NZ) 2012",
            "breeder": "Golden Eye Trust",
        }
        r = client.post("/api/horses", json=payload)
        assert r.status_code == 200
        assert r.json["success"] is True
        assert r.json["data"]["microchip"] == payload["microchip"]

    def test_create_horse_duplicate(self, client):
        # create the horse first
        payload = {
            "microchip": "985125000126462",
            "name": "Prudentia (NZ) 2021",
            "foaling_date": "2021-10-01",
            "sex": "filly",
        }
        r = client.post("/api/horses", json=payload)
        assert r.status_code == 200
        # now try duplicate
        r2 = client.post("/api/horses", json=payload)
        assert r2.status_code == 409
        assert r2.json["success"] is False

    def test_get_horse(self, client):
        payload = {
            "microchip": "985125000126462",
            "name": "Prudentia (NZ) 2021",
            "foaling_date": "2021-10-01",
            "sex": "filly",
        }
        client.post("/api/horses", json=payload)
        r = client.get("/api/horses/985125000126462")
        assert r.status_code == 200
        assert r.json["success"] is True
        assert r.json["data"]["name"] == "Prudentia (NZ) 2021"

    def test_get_horse_not_found(self, client):
        r = client.get("/api/horses/000000000000000")
        assert r.status_code == 404
        assert r.json["success"] is False

    def test_update_horse(self, client):
        payload = {
            "microchip": "985125000126462",
            "name": "Prudentia (NZ) 2021",
            "foaling_date": "2021-10-01",
            "sex": "filly",
        }
        client.post("/api/horses", json=payload)
        r = client.patch("/api/horses/985125000126462", json={"colour": "Chestnut"})
        assert r.status_code == 200
        assert r.json["success"] is True
        r2 = client.get("/api/horses/985125000126462")
        assert r2.json["data"]["colour"] == "Chestnut"

    def test_delete_horse(self, client):
        payload = {
            "microchip": "985125000126462",
            "name": "Prudentia (NZ) 2021",
            "foaling_date": "2021-10-01",
            "sex": "filly",
        }
        client.post("/api/horses", json=payload)
        r = client.delete("/api/horses/985125000126462")
        assert r.status_code == 200
        assert r.json["success"] is True
        r2 = client.get("/api/horses/985125000126462")
        assert r2.status_code == 404

    @pytest.mark.integration
    def test_lookup_horse(self, client):
        """May fail if loveracing.nz blocks scraping."""
        r = client.post("/api/horses/lookup", json={"microchip": "985125000126462"})
        # We accept either success or a graceful failure message
        assert r.status_code in (200, 400)
        assert "success" in r.json


# ─── Owner CRUD ──────────────────────────────────────────────────────────────

class TestOwnerCrud:
    def test_list_owners_empty(self, client):
        r = client.get("/api/owners")
        assert r.status_code == 200
        assert r.json["success"] is True
        assert r.json["data"] == []

    def test_create_owner(self, client):
        payload = {"name": "Golden Eye Trust", "email": "info@goldeneye.nz"}
        r = client.post("/api/owners", json=payload)
        assert r.status_code == 200
        assert r.json["success"] is True
        assert r.json["data"]["id"]
        assert r.json["data"]["name"] == payload["name"]
        # stash id for later
        client.__owner_id = r.json["data"]["id"]

    def test_get_owner(self, client):
        # create first
        r = client.post("/api/owners", json={"name": "Test Owner", "email": "test@example.com"})
        oid = r.json["data"]["id"]
        r2 = client.get(f"/api/owners/{oid}")
        assert r2.status_code == 200
        assert r2.json["data"]["name"] == "Test Owner"

    def test_update_owner(self, client):
        r = client.post("/api/owners", json={"name": "Update Me", "email": "up@example.com"})
        oid = r.json["data"]["id"]
        r2 = client.patch(f"/api/owners/{oid}", json={"phone": "+64 21 123 4567"})
        assert r2.status_code == 200
        r3 = client.get(f"/api/owners/{oid}")
        assert r3.json["data"]["phone"] == "+64 21 123 4567"

    def test_delete_owner(self, client):
        r = client.post("/api/owners", json={"name": "Delete Me", "email": "del@example.com"})
        oid = r.json["data"]["id"]
        r2 = client.delete(f"/api/owners/{oid}")
        assert r2.status_code == 200
        r3 = client.get(f"/api/owners/{oid}")
        assert r3.status_code == 404


# ─── Trainer CRUD ──────────────────────────────────────────────────────────────

class TestTrainerCrud:
    def test_list_trainers_empty(self, client):
        r = client.get("/api/trainers")
        assert r.status_code == 200
        assert r.json["success"] is True
        assert r.json["data"] == []

    def test_create_trainer(self, client):
        payload = {
            "name": "Sam Spratt",
            "stable_name": "Evolution Stables",
            "location": "Cambridge, NZ",
            "email": "sam@evolutionstables.nz",
        }
        r = client.post("/api/trainers", json=payload)
        assert r.status_code == 200
        assert r.json["success"] is True
        assert r.json["data"]["id"]

    def test_get_trainer(self, client):
        r = client.post("/api/trainers", json={
            "name": "Get Me",
            "stable_name": "Stable",
            "location": "NZ",
            "email": "get@example.com",
        })
        tid = r.json["data"]["id"]
        r2 = client.get(f"/api/trainers/{tid}")
        assert r2.status_code == 200
        assert r2.json["data"]["name"] == "Get Me"

    def test_update_trainer(self, client):
        r = client.post("/api/trainers", json={
            "name": "Update Me",
            "stable_name": "Stable",
            "location": "NZ",
            "email": "up@example.com",
        })
        tid = r.json["data"]["id"]
        r2 = client.patch(f"/api/trainers/{tid}", json={"bio": "Champion trainer"})
        assert r2.status_code == 200
        r3 = client.get(f"/api/trainers/{tid}")
        assert r3.json["data"]["bio"] == "Champion trainer"

    def test_delete_trainer(self, client):
        r = client.post("/api/trainers", json={
            "name": "Delete Me",
            "stable_name": "Stable",
            "location": "NZ",
            "email": "del@example.com",
        })
        tid = r.json["data"]["id"]
        r2 = client.delete(f"/api/trainers/{tid}")
        assert r2.status_code == 200
        r3 = client.get(f"/api/trainers/{tid}")
        assert r3.status_code == 404
