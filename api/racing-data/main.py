"""
Evolution Racing Data API — Cloud Function Entry Point

Scrapes race histories from loveracing.nz and stores structured results
in Firestore subcollection: horses/{microchip}/races

Routes:
  /racing-data/loveracing/{loveracing_id}  — Trigger scrape for one horse
  /racing-data/horses/{loveracing_id}       — Get stored race history + summary
  /racing-data/batch/season                — Batch scrape a season
  /racing-data/batch/{batch_id}            — Get batch status
"""

import functions_framework
from flask import Request, jsonify

from routes import loveracing, results, batch


@functions_framework.http
def racing_data(request: Request):
    """Main entry point for the racing-data Cloud Function."""
    path = request.path or ""
    method = request.method

    # ── Single horse scrape ─────────────────────────────────────
    if path.startswith("/racing-data/loveracing/") and method == "POST":
        loveracing_id = path.split("/")[-1]
        return loveracing.scrape_horse(request, loveracing_id)

    # ── Get stored results ──────────────────────────────────────
    if path.startswith("/racing-data/horses/") and method == "GET":
        loveracing_id = path.split("/")[-1]
        return results.get_races(request, loveracing_id)

    # ── Batch scrape ────────────────────────────────────────────
    if path == "/racing-data/batch/season" and method == "POST":
        return batch.scrape_season(request)

    # ── Batch status ────────────────────────────────────────────
    if path.startswith("/racing-data/batch/") and method == "GET":
        batch_id = path.split("/")[-1]
        return batch.get_batch_status(request, batch_id)

    return jsonify({"error": "Not found", "path": path, "method": method}), 404
