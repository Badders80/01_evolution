import sys
from pathlib import Path
import json

sys.path.insert(0, str(Path(__file__).parent))
from admin.db import SessionLocal
from sync_service import preview_website_sync, build_website_payloads

session = SessionLocal()
try:
    payloads = build_website_payloads(session)
    print("=== Generated HLTs Payload from Mission Control DB ===")
    for hlt in payloads["hlts"]:
        print(f"  {hlt['id']} ({hlt['horse_name']}): campaign_status={hlt['campaign_status']}, shares_sold={hlt['shares_sold']}, marketplace_visible={hlt['marketplace_visible']}")

    diff = preview_website_sync(session)
    print("\n=== Sync Diff vs src/data/hlts.json ===")
    print(json.dumps(diff, indent=2))
finally:
    session.close()
