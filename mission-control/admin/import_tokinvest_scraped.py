#!/usr/bin/env python3
"""
Import Tokinvest portal scrapes into Mission Control authoring SSOT.

Source: /home/evo/Tokinvest/raw/scraped/
Target files: _assets/horses/{slug}/documents/…
Target meta: Document rows + HLT pds/sa status when packs present.

Does NOT publish to 02_website/public/documents/ (investor-facing still manual).
"""

from __future__ import annotations

import hashlib
import shutil
import uuid
from pathlib import Path

from admin.db import Document, HLT, Horse, SessionLocal, init_db, utc_now

SCRAPED = Path("/home/evo/Tokinvest/raw/scraped")
ASSETS = Path(__file__).resolve().parents[3] / "_assets" / "horses"

# MC slug → scrape folder (on disk)
SCRAPE_FOLDERS = {
    "first-gear": "first-gear-2",
    "prudentia": "prudentia-10",
    "hottathanafantasy": "hottathanafantasy-11",
    "i-stole-a-manolo": "I_Stole_A_Manolo-14",
}

# filename fragment → (doc_type, relative path under documents/)
# Prefer canonical names for pds/sa; type folders for the rest.
DOC_MAP = [
    ("__pds.pdf", "pds", "pds.pdf"),
    ("__syndicate-agreement.pdf", "sa", "sa.pdf"),
    ("__whitepaper.pdf", "whitepaper", "whitepaper/tokinvest-whitepaper.pdf"),
    ("-whitepapaer.pdf", "whitepaper", "whitepaper/tokinvest-whitepaper.pdf"),  # typo in scrape
    ("__vara-risk-disclosure.pdf", "risk", "risk/tokinvest-vara-risk-disclosure.pdf"),
    ("__vara-issuer-declaration.pdf", "issuer_declaration", "other/tokinvest-vara-issuer-declaration.pdf"),
    ("-Q2Report.pdf", "quarterly", "other/tokinvest-q2-report.pdf"),
]


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()[:16]


def _match_doc(filename: str) -> tuple[str, str] | None:
    low = filename.lower()
    # Order matters: more specific first
    if "syndicate" in low and low.endswith(".pdf"):
        return "sa", "sa.pdf"
    if "__pds" in low or low.endswith("-pds.pdf") or low.endswith("_pds.pdf"):
        return "pds", "pds.pdf"
    if "whitepaper" in low or "whitepapaer" in low:
        return "whitepaper", "whitepaper/tokinvest-whitepaper.pdf"
    if "risk" in low and "disclosure" in low:
        return "risk", "risk/tokinvest-vara-risk-disclosure.pdf"
    if "issuer" in low and "declaration" in low:
        return "issuer_declaration", "other/tokinvest-vara-issuer-declaration.pdf"
    if "q2" in low and "report" in low:
        return "quarterly", "other/tokinvest-q2-report.pdf"
    return None


def import_all(*, dry_run: bool = False) -> list[dict]:
    init_db()
    db = SessionLocal()
    log: list[dict] = []
    try:
        horses = {h.name_slug: h for h in db.query(Horse).all() if h.name_slug}
        hlts_by_chip = {}
        for hlt in db.query(HLT).all():
            hlts_by_chip[hlt.horse_microchip] = hlt

        for slug, folder_name in SCRAPE_FOLDERS.items():
            horse = horses.get(slug)
            if not horse:
                log.append({"slug": slug, "error": "horse not in MC"})
                continue
            hlt = hlts_by_chip.get(horse.microchip)
            if not hlt:
                log.append({"slug": slug, "error": "no HLT"})
                continue

            pdf_dir = SCRAPED / folder_name / "pdfs"
            if not pdf_dir.is_dir():
                log.append({"slug": slug, "error": f"missing {pdf_dir}"})
                continue

            dest_root = ASSETS / slug / "documents"
            for sub in ("risk", "whitepaper", "other", "investor-packs", "vet", "valuation"):
                (dest_root / sub).mkdir(parents=True, exist_ok=True)

            saw_pds = False
            saw_sa = False

            for pdf in sorted(pdf_dir.glob("*.pdf")):
                mapped = _match_doc(pdf.name)
                if not mapped:
                    log.append({"slug": slug, "skip": pdf.name, "reason": "unmapped type"})
                    continue
                doc_type, rel = mapped
                dest = dest_root / rel
                dest.parent.mkdir(parents=True, exist_ok=True)

                if dry_run:
                    log.append({"slug": slug, "would_copy": pdf.name, "→": str(dest.relative_to(ASSETS.parent.parent))})
                    continue

                shutil.copy2(pdf, dest)
                rel_repo = f"_assets/horses/{slug}/documents/{rel}"
                file_hash = _sha256(dest)

                # Idempotent: skip new Document row if same path already registered
                existing = (
                    db.query(Document)
                    .filter_by(hlt_id=hlt.id, file_path=rel_repo)
                    .first()
                )
                if existing:
                    existing.file_name = dest.name
                    existing.mime_type = "application/pdf"
                    existing.status = "draft"  # scraped / archive — not auto-locked
                    existing.doc_type = doc_type
                    doc_id = existing.id
                    action = "updated_row"
                else:
                    doc_id = uuid.uuid4().hex[:12]
                    db.add(
                        Document(
                            id=doc_id,
                            hlt_id=hlt.id,
                            doc_type=doc_type,
                            file_path=rel_repo,
                            file_name=dest.name,
                            mime_type="application/pdf",
                            status="draft",
                            created_at=utc_now(),
                        )
                    )
                    action = "created_row"

                if doc_type == "pds":
                    saw_pds = True
                if doc_type == "sa":
                    saw_sa = True

                log.append({
                    "slug": slug,
                    "hlt": hlt.id,
                    "doc_type": doc_type,
                    "src": pdf.name,
                    "dest": rel_repo,
                    "sha16": file_hash,
                    "action": action,
                })

            if saw_pds and hlt.pds_status in (None, "", "pending"):
                hlt.pds_status = "draft"
            if saw_sa and hlt.sa_status in (None, "", "pending"):
                hlt.sa_status = "draft"
            hlt.updated_at = utc_now()

        if not dry_run:
            db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
    return log


if __name__ == "__main__":
    import json
    import sys

    dry = "--dry-run" in sys.argv
    rows = import_all(dry_run=dry)
    print(json.dumps(rows, indent=2))
    print(f"\n{'DRY RUN' if dry else 'IMPORTED'}: {len(rows)} log lines")
