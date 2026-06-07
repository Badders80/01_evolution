"""
Route: /racing-data/batch/season

Batch scrape all horses in a given racing season.
"""

import uuid
from datetime import date
from flask import Request, jsonify
from google.cloud import firestore

from adapters.loveracing import fetch_html
from store import get_horse_doc_id


def scrape_season(request: Request):
    """
    POST /racing-data/batch/season

    Body:
      {
        "season": "2024/25",
        "horse_ids": [427416, 428364, ...],
        "engine_preference": "webclaw" | "scrapling"
      }

    Returns:
      {
        "batch_id": "batch-abc123",
        "status": "queued",
        "season": "2024/25",
        "total_horses": 42,
        "message": "Batch scrape queued",
        "jobs": [
          {"loveracing_id": 427416, "job_id": "job-xyz", "status": "queued"},
          ...
        ]
      }
    """
    try:
        data = request.get_json(silent=True) or {}
        season = data.get("season")
        horse_ids = data.get("horse_ids", [])
        engine_preference = data.get("engine_preference", "webclaw")

        if not season:
            return jsonify({
                "error": "season is required",
                "status": "failed",
            }), 400

        if not horse_ids:
            return jsonify({
                "error": "horse_ids list is required",
                "status": "failed",
            }), 400

        # Validate season format (YYYY/YY)
        if not isinstance(season, str) or "/" not in season:
            return jsonify({
                "error": "season must be in format 'YYYY/YY' (e.g., '2024/25')",
                "status": "failed",
            }), 400

        batch_id = f"batch-{uuid.uuid4().hex[:8]}"
        db = firestore.Client()

        # Create batch job document
        batch_ref = db.collection("racing_data_batches").document(batch_id)
        batch_data = {
            "batch_id": batch_id,
            "season": season,
            "horse_ids": horse_ids,
            "engine_preference": engine_preference,
            "total_horses": len(horse_ids),
            "status": "queued",
            "created_at": firestore.SERVER_TIMESTAMP,
            "updated_at": firestore.SERVER_TIMESTAMP,
        }
        batch_ref.set(batch_data)

        # Create individual job documents for each horse
        jobs = []
        for loveracing_id in horse_ids:
            job_id = f"job-{uuid.uuid4().hex[:8]}"
            job_ref = batch_ref.collection("jobs").document(job_id)

            # Check if horse already exists in Firestore
            horse_doc_id = get_horse_doc_id_by_loveracing_id(loveracing_id)

            job_data = {
                "job_id": job_id,
                "batch_id": batch_id,
                "loveracing_id": loveracing_id,
                "horse_doc_id": horse_doc_id,
                "status": "queued",
                "created_at": firestore.SERVER_TIMESTAMP,
                "updated_at": firestore.SERVER_TIMESTAMP,
            }
            job_ref.set(job_data)
            jobs.append({
                "loveracing_id": loveracing_id,
                "job_id": job_id,
                "status": "queued",
            })

        return jsonify({
            "batch_id": batch_id,
            "status": "queued",
            "season": season,
            "total_horses": len(horse_ids),
            "message": f"Batch scrape queued for {len(horse_ids)} horses",
            "jobs": jobs,
        }), 200

    except Exception as e:
        return jsonify({
            "error": str(e),
            "status": "failed",
        }), 500


def get_horse_doc_id_by_loveracing_id(loveracing_id: int) -> str | None:
    """Get horse document ID (microchip) by loveracing_id."""
    db = firestore.Client()
    docs = db.collection("horses").where("loveracing_id", "==", loveracing_id).limit(1).get()
    if docs:
        return docs[0].id
    return None


def get_batch_status(request: Request, batch_id: str):
    """
    GET /racing-data/batch/{batch_id}

    Returns status of a batch scrape job.
    """
    try:
        db = firestore.Client()
        batch_ref = db.collection("racing_data_batches").document(batch_id)
        batch_doc = batch_ref.get()

        if not batch_doc.exists:
            return jsonify({
                "error": f"Batch {batch_id} not found",
            }), 404

        batch_data = batch_doc.to_dict()

        # Get job statuses
        jobs_ref = batch_ref.collection("jobs")
        job_docs = jobs_ref.get()
        jobs = []
        for job_doc in job_docs:
            job_data = job_doc.to_dict()
            job_data["id"] = job_doc.id
            jobs.append(job_data)

        # Compute progress
        total = len(jobs)
        completed = sum(1 for j in jobs if j.get("status") == "completed")
        failed = sum(1 for j in jobs if j.get("status") == "failed")

        return jsonify({
            **batch_data,
            "jobs": jobs,
            "progress": {
                "total": total,
                "completed": completed,
                "failed": failed,
                "pending": total - completed - failed,
            },
        }), 200

    except Exception as e:
        return jsonify({
            "error": str(e),
        }), 500