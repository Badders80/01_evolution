"""
Route: /racing-data/loveracing/{loveracing_id}

Trigger a scrape for a single horse's full race history.
"""

from flask import Request, jsonify
from datetime import date
from google.cloud import firestore

from adapters import loveracing as loveracing_adapter
from store import (
    write_race_results,
    write_horse_racing_summary,
    get_horse_doc_id,
    get_horse_ref,
)


def scrape_horse(request: Request, loveracing_id: str):
    """
    POST /racing-data/loveracing/{loveracing_id}

    Steps:
      1. Fetch breeding page → parse static identity (LoveracingRef)
      2. Fetch race history → parse all starts (RaceResult[])
      3. Upsert horse record in Firestore (if not exists)
      4. Store races in subcollection horses/{microchip}/races
      5. Compute and store HorseRacingSummary
      6. Return job summary
    """
    loveracing_id_int = int(loveracing_id)

    try:
        # 1. Fetch and parse breeding page
        breeding_url = loveracing_adapter.breeding_url(loveracing_id_int, "")
        breeding_html = loveracing_adapter.fetch_html(breeding_url)
        breeding_data = loveracing_adapter.parse_breeding_page(breeding_html, loveracing_id_int)

        # Validate we got required fields
        microchip = breeding_data.get("microchip")
        if not microchip:
            return jsonify({
                "error": f"Breeding page for {loveracing_id} did not contain microchip",
                "job_id": f"job-{loveracing_id}",
                "status": "failed",
            }), 500

        name_slug = breeding_data.get("name_slug")
        if not name_slug:
            return jsonify({
                "error": f"Breeding page for {loveracing_id} did not contain name_slug",
                "job_id": f"job-{loveracing_id}",
                "status": "failed",
            }), 500

        # 2. Fetch and parse race history
        race_history_url = loveracing_adapter.race_history_url(loveracing_id_int)
        race_html = loveracing_adapter.fetch_html(race_history_url)
        races = loveracing_adapter.parse_race_history(race_html, microchip, loveracing_id_int)

        # 3. Upsert horse record in Firestore
        db = firestore.Client()
        horse_ref = db.collection("horses").document(microchip)
        horse_doc = horse_ref.get()

        if not horse_doc.exists:
            # Create new horse record
            from datetime import datetime
            horse_data = {
                **breeding_data,
                "id": microchip,  # Use microchip as document ID
                "age": (date.today() - breeding_data.get("foaling_date", date.today())).days // 365
                if breeding_data.get("foaling_date") else None,
                "created_at": firestore.SERVER_TIMESTAMP,
                "updated_at": firestore.SERVER_TIMESTAMP,
            }
            # Convert dates to strings
            if isinstance(horse_data.get("foaling_date"), date):
                horse_data["foaling_date"] = horse_data["foaling_date"].isoformat()

            horse_ref.set(horse_data)
        else:
            # Update existing - just update timestamp
            horse_ref.update({"updated_at": firestore.SERVER_TIMESTAMP})

        # 4. Store races in subcollection
        written_race_ids = write_race_results(microchip, races, scraper_version="scraper/loveracing/v0.1")

        # 5. Compute and store summary
        foaling_date = breeding_data.get("foaling_date")
        if isinstance(foaling_date, str):
            foaling_date = date.fromisoformat(foaling_date)

        summary = loveracing_adapter.compute_horse_racing_summary(
            races, microchip, loveracing_id_int, foaling_date=foaling_date
        )
        write_horse_racing_summary(microchip, summary)

        return jsonify({
            "job_id": f"job-{loveracing_id}",
            "status": "completed",
            "horse_microchip": microchip,
            "loveracing_id": loveracing_id_int,
            "horse_name": breeding_data.get("name"),
            "races_found": len(races),
            "races_stored": len(written_race_ids),
            "summary": {
                "total_starts": summary["total_starts"],
                "total_wins": summary["total_wins"],
                "total_places": summary["total_places"],
                "total_earnings_nzd": summary["total_earnings_nzd"],
            },
            "message": f"Scraped {len(races)} races for {breeding_data.get('name')}",
        }), 200

    except Exception as e:
        return jsonify({
            "job_id": f"job-{loveracing_id}",
            "status": "failed",
            "loveracing_id": loveracing_id_int,
            "error": str(e),
        }), 500
