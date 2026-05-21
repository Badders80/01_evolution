"""
Document Generation — Term Sheet, PDS, Syndicate Agreement

Generates DOCX files from HLT data and uploads them to Cloud Storage.
All three documents are generated from the same canonical HLT record.
"""

from flask import Request, jsonify
from google.cloud import firestore, storage
from datetime import datetime
import io

db = firestore.Client()
storage_client = storage.Client()
BUCKET_NAME = "evolution-horse-docs"

VALID_DOC_TYPES = ["term-sheet", "pds", "sa"]


def handle(request: Request, doc_type: str | None = None):
    """Generate a document from an HLT record."""
    if request.method != "POST":
        return jsonify({"error": "Method not allowed. Use POST."}), 405

    if doc_type not in VALID_DOC_TYPES:
        return jsonify({"error": f"Invalid doc type. Must be one of: {VALID_DOC_TYPES}"}), 400

    data = request.get_json(force=True)
    hlt_id = data.get("hlt_id")
    if not hlt_id:
        return jsonify({"error": "hlt_id is required"}), 400

    # Fetch HLT
    hlt_doc = db.collection("hlts").document(hlt_id).get()
    if not hlt_doc.exists:
        return jsonify({"error": f"HLT {hlt_id} not found"}), 404

    hlt_data = hlt_doc.to_dict()

    # Fetch related entities
    horse_docs = db.collection("horses").where("microchip", "==", hlt_data["horse_microchip"]).limit(1).get()
    horse_data = horse_docs[0].to_dict() if horse_docs else {}

    owner_doc = db.collection("owners").document(hlt_data["owner_id"]).get()
    owner_data = owner_doc.to_dict() if owner_doc.exists else {}

    trainer_doc = db.collection("trainers").document(hlt_data["trainer_id"]).get()
    trainer_data = trainer_doc.to_dict() if trainer_doc.exists else {}

    # Generate document
    try:
        doc_bytes = generate_document(doc_type, hlt_data, horse_data, owner_data, trainer_data)
    except Exception as e:
        return jsonify({"error": f"Document generation failed: {str(e)}"}), 500

    # Upload to Cloud Storage
    bucket = storage_client.bucket(BUCKET_NAME)
    file_name = f"{hlt_id}/{doc_type}.docx"
    blob = bucket.blob(file_name)
    blob.upload_from_string(doc_bytes, content_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document")

    gcs_url = f"gs://{BUCKET_NAME}/{file_name}"

    # Update HLT document status
    doc_field = doc_type.replace("-", "_")  # term-sheet → term_sheet
    hlt_doc.reference.update({
        f"documents.{doc_field}.status": "pending",
        f"documents.{doc_field}.gcs_url": gcs_url,
        "updated_at": firestore.SERVER_TIMESTAMP,
    })

    return jsonify({
        "message": f"{doc_type} generated successfully",
        "gcs_url": gcs_url,
        "doc_type": doc_type,
        "hlt_id": hlt_id,
    }), 200


def generate_document(doc_type: str, hlt_data: dict, horse_data: dict, owner_data: dict, trainer_data: dict) -> bytes:
    """
    Generate a DOCX file from HLT data.

    This is a placeholder that creates a minimal valid DOCX.
    The full implementation will use the python-docx library to create
    production-format documents matching the DNA brand system.
    """
    from docx import Document
    from docx.shared import Inches, Pt, RGBColor
    from docx.enum.text import WD_ALIGN_PARAGRAPH

    doc = Document()

    # Brand colors from DNA
    GOLD = RGBColor(0xD4, 0xA9, 0x64)  # #d4a964
    BLACK = RGBColor(0x12, 0x12, 0x12)  # #121212

    # Title
    title = doc.add_heading("", level=0)
    run = title.add_run(f"{doc_type.replace('-', ' ').title()}")
    run.font.size = Pt(24)
    run.font.color.rgb = BLACK

    # Subtitle
    subtitle = doc.add_paragraph()
    run = subtitle.add_run(f"Horse Lease Token — {horse_data.get('name', 'Unknown')}")
    run.font.size = Pt(14)
    run.font.color.rgb = GOLD

    # Horse details
    doc.add_heading("Horse Details", level=1)
    details = [
        ("Name", horse_data.get("name", "—")),
        ("Microchip", horse_data.get("microchip", "—")),
        ("Life Number", horse_data.get("life_number", "—")),
        ("Foaling Date", str(horse_data.get("foaling_date", "—"))),
        ("Sex", horse_data.get("sex", "—")),
        ("Colour", horse_data.get("colour", "—")),
        ("Sire", horse_data.get("sire_name", "—")),
        ("Dam", horse_data.get("dam_name", "—")),
        ("Breeder", horse_data.get("breeder", "—")),
    ]
    table = doc.add_table(rows=len(details), cols=2)
    table.style = "Light List Accent 1"
    for i, (label, value) in enumerate(details):
        table.rows[i].cells[0].text = label
        table.rows[i].cells[1].text = value

    # Owner details
    doc.add_heading("Owner Details", level=1)
    owner_details = [
        ("Name", owner_data.get("name", "—")),
        ("Type", owner_data.get("type", "—")),
        ("Email", owner_data.get("email", "—")),
    ]
    table = doc.add_table(rows=len(owner_details), cols=2)
    table.style = "Light List Accent 1"
    for i, (label, value) in enumerate(owner_details):
        table.rows[i].cells[0].text = label
        table.rows[i].cells[1].text = value

    # Trainer details
    doc.add_heading("Trainer Details", level=1)
    trainer_details = [
        ("Name", trainer_data.get("name", "—")),
        ("Stable", trainer_data.get("stable_name", "—")),
        ("Location", trainer_data.get("location", "—")),
    ]
    table = doc.add_table(rows=len(trainer_details), cols=2)
    table.style = "Light List Accent 1"
    for i, (label, value) in enumerate(trainer_details):
        table.rows[i].cells[0].text = label
        table.rows[i].cells[1].text = value

    # Lease terms
    doc.add_heading("Lease Terms", level=1)
    lease_details = [
        ("Lease Period", f"{hlt_data.get('lease_period_months', '—')} months"),
        ("Lease Start Date", str(hlt_data.get("lease_start_date", "—"))),
        ("Leasehold Stake", f"{hlt_data.get('leasehold_stake_percentage', '—')}%"),
        ("Investor Return", f"{hlt_data.get('investor_return_percentage', '—')}%"),
        ("Syndicate Price", f"${hlt_data.get('syndicate_price_cents', 0) / 100:,.2f} NZD"),
        ("Total Shares", str(hlt_data.get("shares_total", "—"))),
        ("Share Price", f"${hlt_data.get('share_price_cents', 0) / 100:,.2f} NZD"),
    ]
    table = doc.add_table(rows=len(lease_details), cols=2)
    table.style = "Light List Accent 1"
    for i, (label, value) in enumerate(lease_details):
        table.rows[i].cells[0].text = label
        table.rows[i].cells[1].text = value

    # Footer
    doc.add_paragraph("")
    footer = doc.add_paragraph()
    run = footer.add_run("Evolution Stables — Confidential")
    run.font.size = Pt(8)
    run.font.color.rgb = GOLD

    # Save to bytes
    buffer = io.BytesIO()
    doc.save(buffer)
    buffer.seek(0)
    return buffer.getvalue()