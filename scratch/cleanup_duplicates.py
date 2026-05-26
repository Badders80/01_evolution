#!/usr/bin/env python3
"""
Cleanup duplicate horse assets for hottathanafantasy.
"""

import sys
import argparse
import subprocess
import requests
from email.utils import parsedate_to_datetime

ASSETS_API_URL = "https://australia-southeast1-evolution-engine.cloudfunctions.net/assets"

def get_gcloud_token():
    try:
        token = subprocess.check_output(["gcloud", "auth", "print-identity-token"]).decode("utf-8").strip()
        return token
    except Exception as e:
        print(f"[ERROR] Failed to fetch identity token: {e}")
        sys.exit(1)

def main():
    parser = argparse.ArgumentParser(description="Cleanup duplicate assets")
    parser.add_argument("--execute", action="store_true", help="Perform actual deletions")
    args = parser.parse_args()

    token = get_gcloud_token()
    headers = {"Authorization": f"Bearer {token}"}

    print("[INFO] Fetching assets for hottathanafantasy...")
    resp = requests.get(
        f"{ASSETS_API_URL}/retrieve?entity_type=horse&entity_id=hottathanafantasy",
        headers=headers
    )
    resp.raise_for_status()
    data = resp.json()
    assets = data.get("assets", [])

    print(f"[INFO] Retrieved {len(assets)} assets.")

    # Group by file_name
    grouped = {}
    for asset in assets:
        fname = asset.get("file_name")
        if not fname:
            continue
        grouped.setdefault(fname, []).append(asset)

    to_delete = []
    to_keep = []

    for fname, group in grouped.items():
        if len(group) <= 1:
            to_keep.append(group[0])
            continue

        # Parse created_at dates to sort them
        parsed_group = []
        for item in group:
            created_at_str = item.get("created_at")
            try:
                dt = parsedate_to_datetime(created_at_str)
            except Exception:
                dt = parsedate_to_datetime("Mon, 01 Jan 2000 00:00:00 GMT")
            parsed_group.append((dt, item))

        # Sort ascending by date (oldest first)
        parsed_group.sort(key=lambda x: x[0])

        # Keep the newest one (from the second fully successful run)
        newest_item = parsed_group[-1][1]
        to_keep.append(newest_item)

        # Mark all others as duplicates to delete
        for dt, item in parsed_group[:-1]:
            to_delete.append(item)

    print(f"\n[SUMMARY]")
    print(f"Total Unique Files: {len(grouped)}")
    print(f"Duplicates found to delete: {len(to_delete)}")
    print(f"Files to keep: {len(to_keep)}")

    if not to_delete:
        print("[INFO] No duplicates found. Database is already clean.")
        return

    print("\n[PROPOSED DELETIONS]")
    for i, item in enumerate(to_delete, 1):
        print(f" {i:02d}. ID: {item['id']} | File: {item['file_name']} | Created: {item['created_at']}")

    if args.execute:
        print("\n" + "#"*40 + " STARTING DELETIONS " + "#"*40)
        success_count = 0
        for i, item in enumerate(to_delete, 1):
            print(f"[{i}/{len(to_delete)}] Deleting duplicate asset {item['id']} ({item['file_name']})...")
            try:
                del_resp = requests.delete(
                    f"{ASSETS_API_URL}/delete?asset_id={item['id']}",
                    headers=headers
                )
                if del_resp.status_code == 200:
                    print(f"      Deleted successfully!")
                    success_count += 1
                else:
                    print(f"      [ERROR] Deletion failed: Status {del_resp.status_code} - {del_resp.text}")
            except Exception as e:
                print(f"      [ERROR] Exception deleting {item['id']}: {e}")
        print(f"\n[SUCCESS] Deletion completed. {success_count}/{len(to_delete)} duplicate assets removed.")
    else:
        print("\n[NOTICE] Run with '--execute' to perform the actual cleanup.")

if __name__ == "__main__":
    main()
