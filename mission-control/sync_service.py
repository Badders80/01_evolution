"""
Sync Service — Mission Control → website JSON (+ Sidecar Exports).

IMPORTANT:
  - Reads canonical content from 01_evolution/ (identity, race logs, trainer bios, pedigrees).
  - Reads marketplace overrides from MC SQLite (hero pillars, pedigree blurb, trainer commentary, story override).
  - Exports horses.json, trainers.json, pedigrees.json to 02_website/src/data/.
  - Exports sidecars (horse_meta_export.json, lease_export.json) to 01_evolution/mission-control/admin/.
  - Does NOT write hlts.json directly (sync_inventory.py owns hlts.json).
"""

from __future__ import annotations

import json
import os
import shutil
import yaml
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

# Monorepo Paths
TOOLS_DIR = Path(__file__).resolve().parent
ADMIN_DIR = TOOLS_DIR / "admin"
MONOREPO_ROOT = TOOLS_DIR.parents[1]
EVOLUTION_DIR = MONOREPO_ROOT / "01_evolution"
HORSES_DIR = EVOLUTION_DIR / "horses"
STABLES_DIR = EVOLUTION_DIR / "stables"
PEOPLE_DIR = EVOLUTION_DIR / "people"
WEBSITE_DATA_DIR = MONOREPO_ROOT / "02_website" / "src" / "data"

HORSES_JSON_PATH = WEBSITE_DATA_DIR / "horses.json"
TRAINERS_JSON_PATH = WEBSITE_DATA_DIR / "trainers.json"
PEDIGREES_JSON_PATH = WEBSITE_DATA_DIR / "pedigrees.json"
HLTS_JSON_PATH = WEBSITE_DATA_DIR / "hlts.json"

HORSE_META_EXPORT_PATH = ADMIN_DIR / "horse_meta_export.json"
LEASE_EXPORT_PATH = ADMIN_DIR / "lease_export.json"

GSHEET_ID = os.getenv(
    "GOOGLE_SPREADSHEET_ID",
    "1MJvs2zcPsZ6ek_M2LhRP4jecoyheA7Rrkq8EY-8E08I",
)


def _load_json(path: Path) -> Any:
    if not path.is_file():
        return []
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return []


def _parse_frontmatter_and_body(file_path: Path) -> tuple[dict, str]:
    if not file_path.is_file():
        return {}, ""
    try:
        content = file_path.read_text(encoding="utf-8")
        if not content.startswith("---"):
            return {}, content
        parts = content.split("---", 2)
        if len(parts) < 3:
            return {}, content
        meta = yaml.safe_load(parts[1]) or {}
        return meta, parts[2].strip()
    except Exception:
        return {}, ""


def _extract_markdown_section(body: str, section_title: str) -> str:
    lines = body.splitlines()
    capturing = False
    captured_lines = []
    target_header = f"## {section_title.strip().lower()}"
    for line in lines:
        stripped = line.strip().lower()
        if stripped.startswith("## "):
            if stripped == target_header:
                capturing = True
                continue
            elif capturing:
                break
        elif capturing:
            captured_lines.append(line)
    return "\n".join(captured_lines).strip()


def _read_01_stables() -> Dict[str, dict]:
    stables = {}
    if not STABLES_DIR.is_dir():
        return stables
    for stable_folder in STABLES_DIR.iterdir():
        if not stable_folder.is_dir():
            continue
        profile_path = stable_folder / "profile.md"
        if not profile_path.is_file():
            continue
        meta, body = _parse_frontmatter_and_body(profile_path)
        slug = meta.get("slug") or stable_folder.name
        bio = _extract_markdown_section(body, "Profile")
        
        # Contact name lookup from people
        contact_name = ""
        trainers_list = meta.get("trainers") or []
        if isinstance(trainers_list, list) and trainers_list:
            person_slug = trainers_list[0]
            person_profile = PEOPLE_DIR / person_slug / "profile.md"
            if person_profile.is_file():
                pmeta, _ = _parse_frontmatter_and_body(person_profile)
                contact_name = pmeta.get("name") or ""
        
        stables[slug] = {
            "id": meta.get("backend_id") or f"TRN-{slug}",
            "slug": slug,
            "name": meta.get("name") or slug.replace("-", " ").title(),
            "stable_name": meta.get("name") or slug.replace("-", " ").title(),
            "contact_name": contact_name or meta.get("name") or "",
            "location": meta.get("location") or "New Zealand",
            "bio": bio,
            "website": meta.get("website") or "",
            "phone": meta.get("phone") or "",
            "email": meta.get("email") or "",
            "facebook_url": meta.get("facebook") or "",
            "instagram_url": meta.get("instagram") or "",
            "x_url": meta.get("x") or "",
            "notable_wins": meta.get("notable_wins") or [],
        }
    return stables


def _read_01_leases() -> List[dict]:
    leases = []
    if not HORSES_DIR.is_dir():
        return leases
    for horse_dir in sorted(HORSES_DIR.iterdir()):
        if not horse_dir.is_dir():
            continue
        lease_file = horse_dir / "lease.json"
        if not lease_file.exists():
            continue
        data = _load_json(lease_file)
        if isinstance(data, dict) and data.get("lease_id"):
            leases.append(data)
    return leases


def build_website_payloads(db_session) -> Dict[str, Any]:
    """Build horses.json, trainers.json, pedigrees.json, and sidecars from 01_evolution + MC SQLite."""
    from admin.db import Horse as HorseORM, Lease as LeaseORM

    horses_orm = db_session.query(HorseORM).all()
    stables_dict = _read_01_stables()
    leases_list = _read_01_leases()

    # Map stable backend_id -> stable info
    stable_by_backend_id = {s["id"]: s for s in stables_dict.values()}
    stable_by_slug = {s["slug"]: s for s in stables_dict.values()}

    horses_list: List[dict] = []
    horse_meta_export: List[dict] = []
    pedigrees_list: List[dict] = []

    for h in horses_orm:
        slug = h.name_slug or (h.name.lower().replace(" ", "-") if h.name else "")
        horse_dir = HORSES_DIR / slug

        # 1. Read profile.md
        meta, body = _parse_frontmatter_and_body(horse_dir / "profile.md")
        profile_story = _extract_markdown_section(body, "Profile")

        # 2. Read race-record.json
        race_record = _load_json(horse_dir / "race-record.json") if (horse_dir / "race-record.json").is_file() else {}
        starts_raw = race_record.get("starts") or []
        race_log = []
        for r in starts_raw:
            race_log.append({
                "date": r.get("date") or "",
                "venue": r.get("venue") or "",
                "race": r.get("race_name") or r.get("race") or "",
                "trackCondition": r.get("track_condition") or r.get("trackCondition") or "",
                "result": r.get("result") or "",
                "margin": r.get("margin") or "",
                "distance_m": r.get("distance_m"),
                "race_class": r.get("race_class"),
                "jockey": r.get("jockey"),
                "prizemoney_nzd": r.get("prizemoney_nzd"),
                "starting_price": r.get("starting_price"),
            })

        totals = race_record.get("totals") or {}
        starts_count = totals.get("total_starts") if totals.get("total_starts") is not None else getattr(h, "starts_count", 0)
        wins_count = totals.get("total_wins") if totals.get("total_wins") is not None else getattr(h, "wins_count", 0)
        seconds = totals.get("total_seconds") or 0
        thirds = totals.get("total_thirds") or 0
        places_count = (seconds + thirds) if totals.get("total_starts") is not None else getattr(h, "places_count", 0)
        total_earnings_nzd = totals.get("total_earnings_nzd") if totals.get("total_earnings_nzd") is not None else getattr(h, "total_earnings_nzd", None)

        loveracing_id = str(race_record.get("loveracing_id") or getattr(h, "loveracing_id", "") or "")
        breeding_url = race_record.get("source_url") or getattr(h, "breeding_url", "") or (
            f"https://loveracing.nz/Breeding/{loveracing_id}" if loveracing_id else ""
        )
        perf_url = getattr(h, "performance_profile_url", "") or (
            f"https://loveracing.nz/Common/SystemTemplates/Modal/EntryDetail.aspx?DisplayContext=Modal&HorseID={loveracing_id}"
            if loveracing_id else ""
        )

        # 3. Read pedigree.json
        pedigree_data = _load_json(horse_dir / "pedigree.json") if (horse_dir / "pedigree.json").is_file() else {}
        if pedigree_data and isinstance(pedigree_data, dict):
            pedigrees_list.append(pedigree_data)

        dam_sire_name = (
            (pedigree_data.get("dam") or {}).get("dam_sire") or
            (pedigree_data.get("dam") or {}).get("dam_sire_name") or
            getattr(h, "dam_sire_name", None) or ""
        )

        # 4. Link stable & trainer
        stable_slug = meta.get("stable") or ""
        stable_info = stable_by_slug.get(stable_slug) or stable_by_backend_id.get(h.trainer_id or "") or {}
        trainer_id = stable_info.get("id") or h.trainer_id or "TRN-001"
        trainer_name = stable_info.get("name") or "Evolution Stables"
        trainer_stable = stable_info.get("stable_name") or "Partner Stables"
        trainer_location = stable_info.get("location") or "Matamata NZ"
        trainer_contact_name = stable_info.get("contact_name") or trainer_name

        # 5. Overrides & Story Resolution
        mc_story = (getattr(h, "story", None) or "").strip()
        is_placeholder_story = "Marketplace story not filled yet" in mc_story
        story = mc_story if (mc_story and not is_placeholder_story) else (profile_story or mc_story or "In training with partner stables.")

        next_up = (getattr(h, "next_up", None) or "").strip() or "TBD"

        # Transform 3 pillar pairs into hero_pillars array
        pillars = []
        for cat_attr, val_attr in [("pillar1_cat", "pillar1_val"), ("pillar2_cat", "pillar2_val"), ("pillar3_cat", "pillar3_val")]:
            c = (getattr(h, cat_attr, None) or "").strip()
            v = (getattr(h, val_attr, None) or "").strip()
            if c and v:
                pillars.append({"category": c, "value": v})

        pedigree_blurb = (getattr(h, "pedigree_blurb", None) or "").strip()
        trainer_commentary = (getattr(h, "trainer_commentary", None) or "").strip()

        img_path = (
            getattr(h, "image_path", None)
            or getattr(h, "cover_image", None)
            or getattr(h, "image_url", None)
            or f"/images/content/horses/{slug}-BG.png"
        )

        horse_entry = {
            "name": meta.get("name") or h.name or "",
            "display_name": meta.get("name") or h.name or "",
            "slug": slug,
            "microchip": meta.get("microchip") or h.microchip or "",
            "life_number": meta.get("life_number") or getattr(h, "life_number", "") or (f"NZ{loveracing_id}" if loveracing_id else ""),
            "loveracing_id": loveracing_id,
            "foaling_date": meta.get("foaling_date") or str(h.foaling_date or ""),
            "sex": meta.get("sex") or h.sex or "filly",
            "colour": meta.get("colour") or h.colour or "",
            "sire_name": meta.get("sire_name") or h.sire_name or "",
            "dam_name": meta.get("dam_name") or h.dam_name or "",
            "dam_sire_name": dam_sire_name,
            "breeder": meta.get("breeder") or h.breeder or "",
            "status": h.status or "active",
            "image_path": img_path,
            "story": story,
            "next_up": next_up,
            "trainer_id": trainer_id,
            "trainer_name": trainer_name,
            "trainer_stable": trainer_stable,
            "trainer_location": trainer_location,
            "trainer_contact_name": trainer_contact_name,
            "hero_pillars": pillars,
            "pedigree_blurb": pedigree_blurb,
            "trainer_commentary": trainer_commentary,
            "wins": str(wins_count),
            "placed": str(places_count),
            "starts_count": starts_count,
            "total_earnings_nzd": total_earnings_nzd,
            "race_log": race_log,
            "breeding_url": breeding_url,
            "performance_profile_url": perf_url,
            "identity_status": getattr(h, "identity_status", "verified"),
        }

        horses_list.append(horse_entry)

        # Meta sidecar entry for hlts.json consumers
        meta_entry = dict(horse_entry)
        meta_entry["horse_slug"] = slug
        meta_entry["horse_name"] = horse_entry["display_name"]
        meta_entry["has_terms_sheet"] = bool(getattr(h, "has_terms_sheet", False))
        horse_meta_export.append(meta_entry)

    # Trainers list
    trainers_list = list(stables_dict.values())

    return {
        "horses": horses_list,
        "trainers": trainers_list,
        "pedigrees": pedigrees_list,
        "horse_meta_export": horse_meta_export,
        "lease_export": leases_list,
    }


def sync_db_to_website_json(
    db_session,
    *,
    dry_run: bool = False,
    confirm: bool = False,
) -> Dict[str, Any]:
    """Write 01_evolution + MC inventory → website JSON files + sidecars."""
    try:
        payloads = build_website_payloads(db_session)
        if dry_run or not confirm:
            return {
                "success": True,
                "dry_run": True,
                "horses": len(payloads["horses"]),
                "trainers": len(payloads["trainers"]),
                "pedigrees": len(payloads["pedigrees"]),
                "horse_meta_export": len(payloads["horse_meta_export"]),
                "lease_export": len(payloads["lease_export"]),
                "message": "Dry run preview complete. Pass confirm=True to write files.",
            }

        WEBSITE_DATA_DIR.mkdir(parents=True, exist_ok=True)
        ADMIN_DIR.mkdir(parents=True, exist_ok=True)

        # Write website JSON files
        with open(HORSES_JSON_PATH, "w", encoding="utf-8") as f:
            json.dump(payloads["horses"], f, indent=2, ensure_ascii=False)
        print(f"  ✅ horses.json — {len(payloads['horses'])} records")

        with open(TRAINERS_JSON_PATH, "w", encoding="utf-8") as f:
            json.dump(payloads["trainers"], f, indent=2, ensure_ascii=False)
        print(f"  ✅ trainers.json — {len(payloads['trainers'])} records")

        if payloads["pedigrees"]:
            with open(PEDIGREES_JSON_PATH, "w", encoding="utf-8") as f:
                json.dump(payloads["pedigrees"], f, indent=2, ensure_ascii=False)
            print(f"  ✅ pedigrees.json — {len(payloads['pedigrees'])} records")

        # Write sidecars for sync_inventory.py
        with open(HORSE_META_EXPORT_PATH, "w", encoding="utf-8") as f:
            json.dump(payloads["horse_meta_export"], f, indent=2, ensure_ascii=False)
        print(f"  ✅ horse_meta_export.json — {len(payloads['horse_meta_export'])} records")

        with open(LEASE_EXPORT_PATH, "w", encoding="utf-8") as f:
            json.dump(payloads["lease_export"], f, indent=2, ensure_ascii=False)
        print(f"  ✅ lease_export.json — {len(payloads['lease_export'])} records")

        return {
            "success": True,
            "dry_run": False,
            "horses_synced": len(payloads["horses"]),
            "trainers_synced": len(payloads["trainers"]),
            "pedigrees_synced": len(payloads["pedigrees"]),
            "sidecars_exported": 2,
            "json_path": str(WEBSITE_DATA_DIR),
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


if __name__ == "__main__":
    from admin.db import SessionLocal
    db = SessionLocal()
    try:
        print("🔄 Executing Mission Control → website sync_service...")
        res = sync_db_to_website_json(db, confirm=True)
        print("Result:", res)
    finally:
        db.close()
