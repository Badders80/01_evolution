"""
Route: /racing-data/horses/{loveracing_id}

Get stored race history + computed aggregates for a horse.
"""

from flask import Request, jsonify
from google.cloud import firestore

from adapters.loveracing import race_history_url
from store import get_horse_racing_data, get_horse_doc_id, get_horse_ref


def get_races(request: Request, loveracing_id: str):
    """
    GET /racing-data/horses/{loveracing_id}

    Returns:
      {
        "horse": { /* Horse identity */ },
        "races": [ /* Array of RaceResult */ ],
        "summary": { /* Computed aggregates */ },
        "source_url": "https://loveracing.nz/...",
      }
    """
    # Convert loveracing_id to microchip by querying
    db = firestore.Client()
    docs = db.collection("horses").where("loveracing_id", "==", int(loveracing_id)).limit(1).get()

    if not docs:
        return jsonify({
            "error": f"Horse with loveracing_id {loveracing_id} not found",
            "horse": None,
            "races": [],
            "summary": {},
            "source_url": race_history_url(int(loveracing_id)),
        }), 404

    horse_doc = docs[0]
    microchip = horse_doc.to_dict().get("microchip")

    if not microchip:
        return jsonify({
            "error": f"Horse {loveracing_id} has no microchip",
            "horse": None,
            "races": [],
            "summary": {},
            "source_url": race_history_url(int(loveracing_id)),
        }), 404

    # Get racing data from subcollection
    data = get_horse_racing_data(microchip)

    return jsonify({
        "horse": data["horse"],
        "races": data["races"],
        "summary": data["summary"],
        "source_url": race_history_url(int(loveracing_id)),
    }), 200
