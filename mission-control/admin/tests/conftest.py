"""
Test isolation — MUST load before any admin.db / admin_server import.

Sets ADMIN_DB_PATH to a throwaway SQLite file so autouse clean_db
never DELETEs from the operator production DB (admin/ssot_local.db).
"""

from __future__ import annotations

import os
import tempfile
from pathlib import Path

# ── Bind tests to a temp DB *before* collection imports admin_server ─────────
_PROD_DB = (Path(__file__).resolve().parents[1] / "ssot_local.db").resolve()
_TMP_DIR = tempfile.mkdtemp(prefix="mc-pytest-")
_TEST_DB = Path(_TMP_DIR) / "test_ssot.db"

# Refuse to point at production even if env was already set wrong
if os.environ.get("ADMIN_DB_PATH"):
    existing = Path(os.environ["ADMIN_DB_PATH"]).resolve()
    if existing == _PROD_DB:
        raise RuntimeError(
            "ADMIN_DB_PATH points at production ssot_local.db — refusing to run tests. "
            f"Unset it or point at a temp file. prod={_PROD_DB}"
        )

os.environ["ADMIN_DB_PATH"] = str(_TEST_DB)

# Sanity for later fixtures
assert Path(os.environ["ADMIN_DB_PATH"]).resolve() != _PROD_DB


def pytest_configure(config):
    """Fail the session loudly if ENGINE somehow bound to prod."""
    # Import only after env is set (this file already set it)
    from admin import db as admin_db

    bound = Path(admin_db.DB_PATH).resolve()
    if bound == _PROD_DB:
        raise RuntimeError(
            f"FATAL: test ENGINE bound to production DB: {bound}. "
            "conftest isolation failed — aborting before any clean_db."
        )
    config._mc_test_db = bound  # type: ignore[attr-defined]
    config._mc_prod_db = _PROD_DB  # type: ignore[attr-defined]


def pytest_sessionfinish(session, exitstatus):
    """Best-effort cleanup of temp DB file."""
    try:
        if _TEST_DB.is_file():
            _TEST_DB.unlink(missing_ok=True)
    except OSError:
        pass
