"""
Firestore Storage for Racing Data

Stores:
  - RaceResult in horses/{microchip}/races/{race_id} subcollection
  - HorseRacingSummary in horses/{microchip}/summary (single document)
"""

from datetime import date, datetime
from typing import List, Optional
from google.cloud import firestore
from google.cloud.firestore_v1 import SERVER_TIMESTAMP

db = firestore.Client()


# ── RaceResult subcollection ──────────────────────────────────────
def write_race_results(
    microchip: str,
    races: List[dict],
    scraper_version: str = "scraper/loveracing/v0.1",
) -> List[str]:
    """
    Write RaceResult records to horses/{microchip}/races subcollection.

    Uses a composite key for race_id: {race_date}_{venue}_{race_name_slug}
    to enable idempotent upserts (re-scraping same horse won't create duplicates).

    Args:
        microchip: 15-digit horse microchip
        races: List of RaceResult dicts from parse_race_history()
        scraper_version: Version string for traceability

    Returns:
        List of written document IDs
    """
    horse_ref = db.collection("horses").document(microchip)
    races_ref = horse_ref.collection("races")
    written_ids = []

    for race in races:
        # Build deterministic race_id for idempotency
        race_date = race.get("race_date")
        venue = race.get("venue", "UNK")
        race_name = race.get("race_name", "unknown").lower().replace(" ", "-")
        race_name = "".join(c for c in race_name if c.isalnum() or c == "-")[:50]

        if isinstance(race_date, date):
            date_str = race_date.isoformat()
        else:
            date_str = str(race_date).replace("/", "-")[:10]

        race_id = f"{date_str}_{venue}_{race_name}"

        # Prepare document
        doc_data = {
            **race,
            "scraped_at": datetime.utcnow(),
            "scraper_version": scraper_version,
        }
        # Convert date to string for Firestore
        if isinstance(doc_data.get("race_date"), date):
            doc_data["race_date"] = doc_data["race_date"].isoformat()

        doc_ref = races_ref.document(race_id)
        doc_ref.set(doc_data, merge=True)  # merge=True allows idempotent upsert
        written_ids.append(race_id)

    return written_ids


def read_race_results(
    microchip: str,
    limit: Optional[int] = None,
    start_after: Optional[date] = None,
) -> List[dict]:
    """
    Read RaceResult records from horses/{microchip}/races.

    Args:
        microchip: 15-digit horse microchip
        limit: Max number of records to return
        start_after: Only return races after this date (for pagination)

    Returns:
        List of RaceResult dicts (with string dates)
    """
    horse_ref = db.collection("horses").document(microchip)
    races_ref = horse_ref.collection("races")

    query = races_ref.order_by("race_date", direction=firestore.Query.DESCENDING)

    if start_after:
        query = query.start_after({"race_date": start_after.isoformat()})

    if limit:
        query = query.limit(limit)

    docs = query.get()
    results = []
    for doc in docs:
        data = doc.to_dict()
        data["id"] = doc.id
        results.append(data)

    return results


# ── HorseRacingSummary document ───────────────────────────────────
def write_horse_racing_summary(
    microchip: str,
    summary: dict,
) -> str:
    """
    Write HorseRacingSummary to horses/{microchip}/summary.

    Args:
        microchip: 15-digit horse microchip
        summary: Dict from compute_horse_racing_summary()

    Returns:
        Document ID (always "summary")
    """
    horse_ref = db.collection("horses").document(microchip)
    summary_ref = horse_ref.collection("summary").document("summary")

    doc_data = {
        **summary,
        "computed_at": datetime.utcnow(),
    }
    # Convert dates to strings for Firestore
    if isinstance(doc_data.get("first_start_date"), date):
        doc_data["first_start_date"] = doc_data["first_start_date"].isoformat()
    if isinstance(doc_data.get("last_start_date"), date):
        doc_data["last_start_date"] = doc_data["last_start_date"].isoformat()

    summary_ref.set(doc_data, merge=True)
    return "summary"


def read_horse_racing_summary(microchip: str) -> Optional[dict]:
    """
    Read HorseRacingSummary from horses/{microchip}/summary.

    Args:
        microchip: 15-digit horse microchip

    Returns:
        Summary dict or None if not found
    """
    horse_ref = db.collection("horses").document(microchip)
    summary_ref = horse_ref.collection("summary").document("summary")

    doc = summary_ref.get()
    if doc.exists:
        data = doc.to_dict()
        data["id"] = doc.id
        return data
    return None


# ── Helper: Get horse document reference ──────────────────────────
def get_horse_ref(microchip: str):
    """Get horse document reference by microchip (queries by field)."""
    docs = db.collection("horses").where("microchip", "==", microchip).limit(1).get()
    if docs:
        return docs[0].reference
    return None


def get_horse_doc_id(microchip: str) -> Optional[str]:
    """Get horse document ID by microchip."""
    docs = db.collection("horses").where("microchip", "==", microchip).limit(1).get()
    if docs:
        return docs[0].id
    return None


# ── Combined read: races + summary ────────────────────────────────
def get_horse_racing_data(microchip: str, limit: Optional[int] = None) -> dict:
    """
    Get complete racing data for a horse: races + summary.

    Args:
        microchip: 15-digit horse microchip
        limit: Max number of races to return (None = all)

    Returns:
        Dict with 'horse', 'races', 'summary' keys
    """
    horse_ref = get_horse_ref(microchip)
    horse_data = None
    if horse_ref:
        horse_doc = horse_ref.get()
        if horse_doc.exists:
            horse_data = horse_doc.to_dict()
            horse_data["id"] = horse_doc.id

    races = read_race_results(microchip, limit=limit)
    summary = read_horse_racing_summary(microchip)

    return {
        "horse": horse_data,
        "races": races,
        "summary": summary,
    }