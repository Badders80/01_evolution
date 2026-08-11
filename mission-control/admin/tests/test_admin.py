"""Tests for admin_server CRUD endpoints + horse_lookup."""

import json

import pytest
from admin_server import app
from admin.db import ENGINE, init_db, Horse, Owner, Trainer, SessionLocal
from sqlalchemy import inspect


@pytest.fixture
def client():
    app.config["TESTING"] = True
    with app.test_client() as c:
        yield c


@pytest.fixture(autouse=True)
def clean_db():
    """Wipe all entity rows before each test so order doesn't matter.

    HARD GUARD: never run against the operator production ssot_local.db.
    Isolation is set in conftest.py (ADMIN_DB_PATH → temp file before imports).
    """
    from pathlib import Path

    from admin.db import DB_PATH, SessionLocal
    from sqlalchemy import text

    prod = (Path(__file__).resolve().parents[1] / "ssot_local.db").resolve()
    bound = Path(DB_PATH).resolve()
    if bound == prod:
        raise RuntimeError(
            f"REFUSING clean_db on production DB: {bound}. "
            "conftest.py must set ADMIN_DB_PATH to a temp SQLite file."
        )

    db = SessionLocal()
    try:
        for tbl in ["documents", "hlts", "leases", "horses", "owners", "trainers", "governing_bodies"]:
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
        assert b"Mission Control" in r.data

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
            "name": "Lance O'Sullivan & Andrew Scott",
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


# ─── Lease CRUD ──────────────────────────────────────────────────────────────

class TestLeaseCrud:
    def test_list_leases_empty(self, client):
        r = client.get("/api/leases")
        assert r.status_code == 200
        assert r.json["success"] is True
        assert r.json["data"] == []

    def test_create_lease(self, client):
        # need a horse first
        client.post("/api/horses", json={
            "microchip": "985125000126462",
            "name": "Prudentia (NZ) 2021",
            "foaling_date": "2021-10-01",
            "sex": "filly",
        })
        payload = {
            "lease_id": "LSE-002",
            "horse_id": "985125000126462",
            "start_date": "2024-01-01",
            "end_date": "2025-06-30",
            "duration_months": 18,
            "percent_leased": 5,
            "token_count": 20,
            "min_unit_size": 0.25,
            "price_basis": "per_1pct",
            "price_period": "month",
            "price_amount": 65,
            "investor_share_percent": 75,
            "owner_share_percent": 25,
            "platform_fee_percent": 0,
        }
        r = client.post("/api/leases", json=payload)
        assert r.status_code == 200
        assert r.json["success"] is True
        assert r.json["data"]["lease_id"] == "LSE-002"

    def test_create_lease_duplicate(self, client):
        client.post("/api/horses", json={
            "microchip": "985125000126462",
            "name": "Prudentia (NZ) 2021",
            "foaling_date": "2021-10-01",
            "sex": "filly",
        })
        payload = {
            "lease_id": "LSE-002",
            "horse_id": "985125000126462",
            "start_date": "2024-01-01",
            "end_date": "2025-06-30",
            "duration_months": 18,
            "percent_leased": 5,
            "token_count": 20,
            "min_unit_size": 0.25,
            "price_basis": "per_1pct",
            "price_period": "month",
            "price_amount": 65,
            "investor_share_percent": 75,
            "owner_share_percent": 25,
            "platform_fee_percent": 0,
        }
        r1 = client.post("/api/leases", json=payload)
        assert r1.status_code == 200
        r2 = client.post("/api/leases", json=payload)
        assert r2.status_code == 409

    def test_get_lease(self, client):
        client.post("/api/horses", json={
            "microchip": "985125000126462",
            "name": "Prudentia (NZ) 2021",
            "foaling_date": "2021-10-01",
            "sex": "filly",
        })
        payload = {
            "lease_id": "LSE-002",
            "horse_id": "985125000126462",
            "start_date": "2024-01-01",
            "end_date": "2025-06-30",
            "duration_months": 18,
            "percent_leased": 5,
            "token_count": 20,
            "min_unit_size": 0.25,
            "price_basis": "per_1pct",
            "price_period": "month",
            "price_amount": 65,
            "investor_share_percent": 75,
            "owner_share_percent": 25,
            "platform_fee_percent": 0,
        }
        client.post("/api/leases", json=payload)
        r = client.get("/api/leases/LSE-002")
        assert r.status_code == 200
        d = r.json["data"]
        assert d["total_issuance_value_nzd"] == 5850.0
        assert d["token_price_nzd"] == 292.5
        assert d["percent_per_token"] == 0.25

    def test_get_lease_not_found(self, client):
        r = client.get("/api/leases/NONE")
        assert r.status_code == 404


# ─── HLT Workflow ─────────────────────────────────────────────────────────────

class TestHLTWorkflow:
    def test_hlt_workflow_missing_refs(self, client):
        r = client.post("/api/hlts/workflow", json={
            "horse_microchip": "000000000000000",
            "owner_id": "no-one",
            "trainer_id": "no-one",
        })
        assert r.status_code == 404
        assert r.json["success"] is False

    def test_hlt_workflow_success(self, client):
        # Seed entities
        client.post("/api/horses", json={
            "microchip": "985125000126462",
            "name": "Prudentia (NZ) 2021",
            "foaling_date": "2021-10-01",
            "sex": "filly",
        })
        ro = client.post("/api/owners", json={"name": "B.A.X Bloodstock", "email": "info@bax.nz"})
        oid = ro.json["data"]["id"]
        rt = client.post("/api/trainers", json={
            "name": "Wexford Stables",
            "stable_name": "Wexford Stables",
            "location": "Cambridge, NZ",
            "email": "info@wexford.nz",
        })
        tid = rt.json["data"]["id"]

        r = client.post("/api/hlts/workflow", json={
            "horse_microchip": "985125000126462",
            "owner_id": oid,
            "trainer_id": tid,
            "lease_id": "LSE-002",
            "start_date": "2024-01-01",
            "end_date": "2025-06-30",
            "duration_months": 18,
            "percent_leased": 5,
            "token_count": 20,
            "min_unit_size": 0.25,
            "price_basis": "per_1pct",
            "price_period": "month",
            "price_amount": 65,
            "investor_share_percent": 75,
            "owner_share_percent": 25,
            "platform_fee_percent": 0,
        })
        assert r.status_code == 200
        assert r.json["success"] is True
        lease = r.json["data"]["lease"]
        hlt = r.json["data"]["hlt"]
        assert lease["total_issuance_value_nzd"] == 5850.0
        assert lease["token_price_nzd"] == 292.5
        assert lease["percent_per_token"] == 0.25
        assert hlt["status"] == "coming_soon"  # v1 four-state model (not legacy "draft")
        assert hlt["lease_id"] == "LSE-002"

        # verify GET /api/hlts/<id> returns full graph
        r2 = client.get(f"/api/hlts/{hlt['id']}")
        assert r2.status_code == 200
        d = r2.json["data"]
        assert d["horse"]["name"] == "Prudentia (NZ) 2021"
        assert d["owner"]["name"] == "B.A.X Bloodstock"
        assert d["trainer"]["name"] == "Wexford Stables"
        assert d["lease"]["total_issuance_value_nzd"] == 5850.0


# ─── Term Sheet Generation ────────────────────────────────────────────────────

class TestTermSheetGeneration:
    def test_term_sheet_404_missing_hlt(self, client):
        r = client.get("/api/hlts/nope/term-sheet.docx")
        assert r.status_code == 404
        assert r.json["success"] is False

    def test_term_sheet_download_and_status_update(self, client):
        # Seed entities (same pattern as HLT workflow test)
        client.post("/api/horses", json={
            "microchip": "985125000126463",
            "name": "Term Sheet Test Horse",
            "foaling_date": "2022-01-01",
            "sex": "colt",
            "sire_name": "Test Sire",
            "dam_name": "Test Dam",
        })
        ro = client.post("/api/owners", json={
            "name": "Term Sheet Owner",
            "email": "ts@example.com",
            "entity_type": "company",
        })
        oid = ro.json["data"]["id"]
        rt = client.post("/api/trainers", json={
            "name": "Term Sheet Trainer",
            "stable_name": "TS Stables",
            "location": "Auckland",
            "email": "ts-trainer@example.com",
        })
        tid = rt.json["data"]["id"]

        # Create HLT via workflow
        r = client.post("/api/hlts/workflow", json={
            "horse_microchip": "985125000126463",
            "owner_id": oid,
            "trainer_id": tid,
            "lease_id": "LSE-TS-001",
            "start_date": "2024-01-01",
            "end_date": "2024-12-31",
            "duration_months": 12,
            "percent_leased": 10,
            "token_count": 40,
            "min_unit_size": 0.25,
            "price_basis": "per_1pct",
            "price_period": "month",
            "price_amount": 100,
            "investor_share_percent": 75,
            "owner_share_percent": 20,
            "platform_fee_percent": 5,
        })
        assert r.status_code == 200
        hlt_id = r.json["data"]["hlt"]["id"]

        # Verify initial status
        r2 = client.get(f"/api/hlts/{hlt_id}")
        assert r2.json["data"]["term_sheet_status"] == "pending"

        # Download term sheet
        r3 = client.get(f"/api/hlts/{hlt_id}/term-sheet.docx")
        assert r3.status_code == 200
        assert r3.content_type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        assert len(r3.data) > 5000  # Reasonable DOCX size

        # Verify status flipped to complete
        r4 = client.get(f"/api/hlts/{hlt_id}")
        assert r4.json["data"]["term_sheet_status"] == "complete"


# ─── Horse slug uniqueness (P4) ───────────────────────────────────────────────

class TestHorseSlugUniqueness:
    def _make(self, client, microchip, slug):
        return client.post("/api/horses", json={
            "microchip": microchip,
            "name": f"Horse {microchip[-4:]}",
            "foaling_date": "2021-01-01",
            "sex": "filly",
            "name_slug": slug,
        })

    def test_create_duplicate_slug_returns_409(self, client):
        r1 = self._make(client, "985125000126462", "dup-slug")
        assert r1.status_code == 200
        r2 = self._make(client, "985125000126463", "dup-slug")
        assert r2.status_code == 409
        assert r2.json["success"] is False
        assert "slug" in str(r2.json["error"]).lower()

    def test_update_slug_collision_returns_409(self, client):
        self._make(client, "985125000126462", "alpha")
        self._make(client, "985125000126463", "beta")
        r = client.patch("/api/horses/985125000126463", json={"name_slug": "alpha"})
        assert r.status_code == 409
        assert r.json["success"] is False

    def test_update_slug_to_own_value_ok(self, client):
        # A horse re-saving its own current slug must NOT trip the collision check.
        self._make(client, "985125000126462", "alpha")
        r = client.patch("/api/horses/985125000126462", json={"name_slug": "alpha"})
        assert r.status_code == 200
        assert r.json["success"] is True

    def test_create_horse_without_slug_ok(self, client):
        # NULL slug must not collide (partial unique index excludes NULL/empty).
        r1 = client.post("/api/horses", json={
            "microchip": "985125000126462",
            "name": "No Slug One",
            "foaling_date": "2021-01-01",
            "sex": "filly",
        })
        r2 = client.post("/api/horses", json={
            "microchip": "985125000126463",
            "name": "No Slug Two",
            "foaling_date": "2021-01-01",
            "sex": "filly",
        })
        assert r1.status_code == 200
        assert r2.status_code == 200


# ─── Horse performance fields (P1) ────────────────────────────────────────────

PERF_RACE_LOG = json.dumps([
    {
        "date": "2024-12-28", "venue": "Otaki", "race": "1600m", "distance": "1600m",
        "result": "1st", "finish": "1st",
        "trackCondition": "Good", "track_condition": "Good",
        "margin": None, "jockey": None, "class": None,
    }
])


class TestHorsePerformanceColumns:
    def test_perf_columns_exist(self):
        init_db()
        cols = {c["name"] for c in inspect(ENGINE).get_columns("horses")}
        for c in ("starts_count", "wins_count", "places_count",
                  "total_earnings_nzd", "performance_profile_url", "race_log_json"):
            assert c in cols, f"missing perf column: {c}"


class TestHorsePerfCrud:
    def _create(self, client, microchip="985125000126462"):
        client.post("/api/horses", json={
            "microchip": microchip,
            "name": "Prudentia (NZ) 2021",
            "foaling_date": "2021-10-01",
            "sex": "filly",
        })

    def test_patch_perf_scalars_persist(self, client):
        self._create(client)
        r = client.patch("/api/horses/985125000126462", json={
            "starts_count": 10,
            "wins_count": 3,
            "places_count": 2,
            "total_earnings_nzd": 18500.0,
            "performance_profile_url": "https://loveracing.nz/Horse/428364",
        })
        assert r.status_code == 200, r.json
        g = client.get("/api/horses/985125000126462")
        d = g.json["data"]
        assert d["starts_count"] == 10
        assert d["wins_count"] == 3
        assert d["places_count"] == 2
        assert d["total_earnings_nzd"] == 18500.0
        assert d["performance_profile_url"] == "https://loveracing.nz/Horse/428364"

    def test_patch_race_log_json_persists(self, client):
        self._create(client)
        r = client.patch("/api/horses/985125000126462", json={
            "race_log_json": PERF_RACE_LOG,
        })
        assert r.status_code == 200, r.json
        g = client.get("/api/horses/985125000126462")
        assert g.json["data"]["race_log_json"] == PERF_RACE_LOG

    def test_patch_perf_does_not_drop_unsent_fields(self, client):
        # PATCH wins_count alone must not zero out other perf fields.
        self._create(client)
        client.patch("/api/horses/985125000126462", json={
            "wins_count": 3, "places_count": 2, "starts_count": 10,
        })
        client.patch("/api/horses/985125000126462", json={"wins_count": 4})
        d = client.get("/api/horses/985125000126462").json["data"]
        assert d["wins_count"] == 4
        assert d["places_count"] == 2  # unchanged
        assert d["starts_count"] == 10  # unchanged


# ─── Sync payload builder — performance contract (P1) ──────────────────────────

class TestSyncPerformancePayload:
    def _seed_horse_with_perf(self):
        init_db()
        db = SessionLocal()
        try:
            h = Horse(
                microchip="985125000126462",
                name="Prudentia (NZ) 2021",
                name_slug="prudentia",
                foaling_date="2021-10-01",
                sex="filly",
                starts_count=10,
                wins_count=3,
                places_count=2,
                total_earnings_nzd=18500.0,
                performance_profile_url="https://loveracing.nz/Horse/428364",
                race_log_json=PERF_RACE_LOG,
            )
            db.add(h)
            db.commit()
            return db
        finally:
            db.close()

    def test_horses_payload_exports_real_perf(self):
        from sync_service import build_website_payloads
        db = self._seed_horse_with_perf()
        try:
            payloads = build_website_payloads(db)
            h = payloads["horses"][0]
            # wins/placed exported as strings (website consumer expects strings)
            assert h["wins"] == "3"
            assert h["placed"] == "2"
            assert h["starts_count"] == 10
            assert h["total_earnings_nzd"] == 18500.0
            assert h["performance_profile_url"] == "https://loveracing.nz/Horse/428364"
            # race_log parsed to a list matching DetailTabs Race shape + PLAN aliases
            assert isinstance(h["race_log"], list)
            entry = h["race_log"][0]
            assert entry["date"] == "2024-12-28"
            assert entry["venue"] == "Otaki"
            assert entry["race"] == "1600m"        # DetailTabs key
            assert entry["distance"] == "1600m"   # PLAN alias
            assert entry["result"] == "1st"        # DetailTabs key
            assert entry["finish"] == "1st"       # PLAN alias
            assert entry["trackCondition"] == "Good"  # DetailTabs key
            assert entry["track_condition"] == "Good"  # PLAN alias
        finally:
            db.close()

    def test_horses_payload_perf_defaults_when_empty(self):
        from sync_service import build_website_payloads
        init_db()
        db = SessionLocal()
        try:
            h = Horse(
                microchip="985125000126463",
                name="Empty Perf Horse",
                name_slug="empty-perf",
                foaling_date="2021-10-01",
                sex="gelding",
            )
            db.add(h)
            db.commit()
            payloads = build_website_payloads(db)
            row = next(x for x in payloads["horses"] if x["slug"] == "empty-perf")
            # graceful defaults — no crash, no "0" hardcode regression for unset
            assert row["wins"] == "0"
            assert row["placed"] == "0"
            assert row["starts_count"] == 0
            assert row["race_log"] == []
            assert row["performance_profile_url"] == ""
        finally:
            db.close()
