#!/usr/bin/env python3
"""
Google Drive Assets Import Utility
==================================
Downloads horse images and videos from Google Drive folders,
matches them to Firestore horse records (using fallback slugs for horses without microchips),
and uploads them to GCS via the live authenticated Assets API with exact Wexford-style tagging.
"""

import os
import re
import sys
import uuid
import argparse
import subprocess
import requests
import mimetypes

# ─── CONFIGURATION ────────────────────────────────────────────────────────────

SSOT_API_URL = "https://australia-southeast1-evolution-engine.cloudfunctions.net/ssot"
ASSETS_API_URL = "https://australia-southeast1-evolution-engine.cloudfunctions.net/assets"

# Directories
SCRATCH_DIR = os.path.dirname(os.path.abspath(__file__))
IMPORT_BASE_DIR = os.path.join(SCRATCH_DIR, "gdrive_imports")

# Manual mapping for Google Drive folder links provided by the user
FOLDER_CONFIGS = [
    {
        "id": "1yNF_Ju0Gjo7HoimLyamgu3iDY2YBEVfY",
        "name": "folder_13feb",
        "default_horse": "Hottathanafantasy (NZ)",
        "default_date": "2026-02-13",
        "location": "Wexford Stables",
    },
    {
        "id": "1dhJl0rQ5CeFO5cCV8-mivNW-_0CH0w3t",
        "name": "folder_20feb",
        "default_horse": "Hottathanafantasy (NZ)",
        "default_date": "2026-02-20",
        "location": "Wexford Stables",
    },
    {
        "id": "1-ETRFOXonUVpyM46HTAadK7gT0C-_EdB",
        "name": "prudentia_folder_1",
        "default_horse": "Prudentia",
        "default_date": "2026-05-26",
        "location": "Wexford Stables",
    },
    {
        "id": "1WdD2BtsFh7xwExr07cmMx7Lu40uGCkEW",
        "name": "prudentia_folder_2",
        "default_horse": "Prudentia",
        "default_date": "2026-05-26",
        "location": "Wexford Stables",
    },
    {
        "id": "1KAnlbVPqCpkQmOC-XB5Gv6d4DdblVb7u",
        "name": "prudentia_folder_3",
        "default_horse": "Prudentia",
        "default_date": "2026-05-26",
        "location": "Wexford Stables",
    }
]

# ─── COLOR LOGGING HELPERS ────────────────────────────────────────────────────

def log_info(msg):
    print(f"\033[94m[INFO]\033[0m {msg}")

def log_success(msg):
    print(f"\033[92m[SUCCESS]\033[0m {msg}")

def log_warning(msg):
    print(f"\033[93m[WARNING]\033[0m {msg}")

def log_error(msg):
    print(f"\033[91m[ERROR]\033[0m {msg}", file=sys.stderr)

# ─── AUTHENTICATION ───────────────────────────────────────────────────────────

def get_gcloud_token():
    """Fetch active gcloud identity token for bearer auth."""
    try:
        token = subprocess.check_output(["gcloud", "auth", "print-identity-token"]).decode("utf-8").strip()
        return token
    except Exception as e:
        log_error(f"Failed to fetch gcloud identity token: {e}")
        log_error("Make sure you are logged in via 'gcloud auth login' and have active credentials.")
        sys.exit(1)

# ─── RESOLVE HORSES FROM SSOT ──────────────────────────────────────────────────

def fetch_registered_horses(token):
    """Retrieve all horse records from live SSOT API."""
    log_info("Fetching registered horses from live SSOT API...")
    headers = {"Authorization": f"Bearer {token}"}
    try:
        resp = requests.get(f"{SSOT_API_URL}/horses", headers=headers, timeout=15)
        resp.raise_for_status()
        horses = resp.json()
        log_success(f"Retrieved {len(horses)} horse records.")
        return horses
    except Exception as e:
        log_error(f"Failed to load horses from SSOT API: {e}")
        sys.exit(1)

def slugify(text):
    """Convert horse name to slug fallback."""
    if not text:
        return ""
    text = text.lower().strip()
    text = re.sub(r"\([^)]*\)", "", text) # Remove parentheticals
    text = re.sub(r"[^a-z0-9]+", "-", text) # Alphanumeric to hyphens
    text = re.sub(r"-{2,}", "-", text) # Remove multi-hyphens
    return text.strip("-")

def find_matching_horse(file_path, default_horse_name, horses_list):
    """Match file path or folder context to registered horse record."""
    path_lower = file_path.lower()
    
    # Check for direct horse names in the filename or path
    for horse in horses_list:
        # Check standard fields
        name = horse.get("name") or horse.get("horse_name") or ""
        slug = slugify(name)
        
        # Check nested identity fields (like in I Stole A Manolo)
        if not name and "identity" in horse:
            name = horse["identity"].get("horse_name", "")
            slug = slugify(name)

        if not name:
            continue

        name_lower = name.lower()
        # Strip trailing parentheticals for matching (e.g. Hottathanafantasy (NZ) -> hottathanafantasy)
        short_name = re.sub(r"\([^)]*\)", "", name_lower).strip()

        if short_name in path_lower or slug in path_lower:
            return horse

    # Fallback to default folder horse
    for horse in horses_list:
        name = horse.get("name") or horse.get("horse_name") or ""
        if not name and "identity" in horse:
            name = horse["identity"].get("horse_name", "")
            
        if name and name.lower() == default_horse_name.lower():
            return horse
            
    return None

# ─── RESOLVE DATE FROM CONTEXT ────────────────────────────────────────────────

def extract_date_from_path(file_path, default_date):
    """Extract date (YYYY-MM-DD) from path or fallback."""
    file_name = os.path.basename(file_path)
    
    # Check filename first for explicit date indicators
    # Pattern 1: YYYY-MM-DD in filename
    match = re.search(r"(\d{4})[-_](\d{2})[-_](\d{2})", file_name)
    if match:
        return f"{match.group(1)}-{match.group(2)}-{match.group(3)}"
        
    # Pattern 2: DDMonYYYY or DDMon in filename (e.g. 20Feb2026 or 24March)
    match = re.search(r"(\d{1,2})([A-Za-z]{3,9})(\d{4})?", file_name)
    if match:
        day = int(match.group(1))
        month_str = match.group(2).lower()
        year = match.group(3) or "2026"
        
        months = {
            "jan": "01", "feb": "02", "mar": "03", "apr": "04", "may": "05", "jun": "06",
            "jul": "07", "aug": "08", "sep": "09", "oct": "10", "nov": "11", "dec": "12",
            "january": "01", "february": "02", "march": "03", "april": "04", "may": "05", "june": "06",
            "july": "07", "august": "08", "september": "09", "october": "10", "november": "11", "december": "12"
        }
        month = months.get(month_str[:3])
        if month:
            return f"{year}-{month}-{day:02d}"
            
    # Pattern 3: YYYYMMDD in filename (e.g. IMG-20260204-WA0001)
    match = re.search(r"(\d{4})(\d{2})(\d{2})", file_name)
    if match:
        return f"{match.group(1)}-{match.group(2)}-{match.group(3)}"

    # Fallback to default_date from folder configuration
    return default_date

# ─── DOWNLOAD DRIVER ──────────────────────────────────────────────────────────

def download_all_folders():
    """Download Google Drive folders via gdown."""
    import gdown
    log_info(f"Preparing to download Google Drive folders into: {IMPORT_BASE_DIR}")
    os.makedirs(IMPORT_BASE_DIR, exist_ok=True)
    
    for config in FOLDER_CONFIGS:
        target_path = os.path.join(IMPORT_BASE_DIR, config["name"])
        if os.path.exists(target_path) and len(os.listdir(target_path)) > 0:
            log_info(f"Folder '{config['name']}' already downloaded at {target_path}. Skipping download.")
            continue
            
        log_info(f"Downloading folder '{config['name']}' ({config['id']}) from Google Drive...")
        try:
            gdown.download_folder(
                id=config["id"],
                output=target_path,
                quiet=False,
                use_cookies=False
            )
            log_success(f"Downloaded folder: {config['name']}")
        except Exception as e:
            log_error(f"gdown failed for folder {config['name']}: {e}")
            log_warning("Ensure the Google Drive folder is set to 'Anyone with the link can view'.")

# ─── SCAN AND COMPILE MIGRATION MAP ───────────────────────────────────────────

def scan_files_and_map(horses_list):
    """Scan imported files and build proposed uploads metadata list."""
    log_info("Scanning downloaded files to map metadata...")
    proposed_uploads = []
    seen_filenames = set() # Track already-processed filenames to avoid duplicates
    
    if not os.path.exists(IMPORT_BASE_DIR):
        log_error(f"Imports directory does not exist: {IMPORT_BASE_DIR}")
        return []
        
    for config in FOLDER_CONFIGS:
        folder_path = os.path.join(IMPORT_BASE_DIR, config["name"])
        if not os.path.exists(folder_path):
            continue
            
        for root, _, files in os.walk(folder_path):
            for file_name in files:
                # Ignore hidden files
                if file_name.startswith("."):
                    continue
                    
                file_path = os.path.join(root, file_name)
                
                # Filter by media types (images and videos)
                mime_type, _ = mimetypes.guess_type(file_path)
                if not mime_type:
                    ext = os.path.splitext(file_name)[1].lower()
                    if ext in [".mp4", ".mov", ".webm"]:
                        mime_type = "video/mp4"
                    elif ext in [".jpg", ".jpeg", ".png", ".webp"]:
                        mime_type = "image/jpeg"
                    else:
                        continue # Skip unhandled file types
                        
                # Check for duplicate filename to avoid duplicate GCS uploads
                if file_name in seen_filenames:
                    log_info(f"Skipping duplicate file '{file_name}' already scanned in earlier folder context.")
                    continue
                seen_filenames.add(file_name)
                
                # Determine asset type category
                asset_category = "image" if mime_type.startswith("image/") else "document"
                media_type_label = "image" if asset_category == "image" else "video"
                
                # Match to horse
                matched_horse = find_matching_horse(file_path, config["default_horse"], horses_list)
                if not matched_horse:
                    log_warning(f"Could not match horse for file: {file_path}. Skipping.")
                    continue
                    
                horse_name = matched_horse.get("name") or matched_horse.get("horse_name")
                if not horse_name and "identity" in matched_horse:
                    horse_name = matched_horse["identity"].get("horse_name")
                    
                # Match horse identifier (microchip number, or slug fallback)
                horse_id = (
                    matched_horse.get("microchip_number") 
                    or matched_horse.get("microchip") 
                    or (matched_horse.get("identity") and matched_horse["identity"].get("microchip_number"))
                    or slugify(horse_name) # Fallback to slug if no microchip
                )
                
                # Match Date
                date_str = extract_date_from_path(file_path, config["default_date"])
                
                # Prepare Tags (same layout as Wexford email updates)
                tags = f"{media_type_label},update,{horse_name},{date_str}"
                alt = f"{media_type_label.capitalize()} update for {horse_name} — {date_str} at {config['location']}"
                
                proposed_uploads.append({
                    "file_path": file_path,
                    "file_name": file_name,
                    "mime_type": mime_type,
                    "horse_name": horse_name,
                    "horse_id": horse_id,
                    "date": date_str,
                    "tags": tags,
                    "alt": alt,
                    "asset_category": asset_category
                })
                
    return proposed_uploads

# ─── UPLOAD AND EXECUTE ───────────────────────────────────────────────────────

def execute_uploads(proposed_uploads, token):
    """Post proposed uploads to live Assets API."""
    log_info(f"Starting execution of {len(proposed_uploads)} uploads to Assets API...")
    headers = {"Authorization": f"Bearer {token}"}
    success_count = 0
    
    for i, item in enumerate(proposed_uploads, 1):
        log_info(f"[{i}/{len(proposed_uploads)}] Uploading {item['file_name']} for {item['horse_name']}...")
        
        try:
            with open(item["file_path"], "rb") as f:
                files = {
                    "file": (item["file_name"], f, item["mime_type"])
                }
                data = {
                    "entity_type": "horse",
                    "entity_id": item["horse_id"],
                    "tags": item["tags"],
                    "alt": item["alt"],
                    "uploaded_by": "gdrive-import"
                }
                
                resp = requests.post(
                    f"{ASSETS_API_URL}/upload",
                    headers=headers,
                    files=files,
                    data=data,
                    timeout=180 # Allow ample time for large video uploads
                )
                
                if resp.status_code in (200, 201):
                    log_success(f"Successfully uploaded: {item['file_name']} -> Asset Registered!")
                    success_count += 1
                else:
                    log_error(f"Failed to upload {item['file_name']}: Status {resp.status_code} - {resp.text}")
                    
        except Exception as e:
            log_error(f"Error uploading {item['file_name']}: {e}")
            
    log_success(f"\nMigration execution finished! {success_count}/{len(proposed_uploads)} files migrated successfully.")

# ─── MAIN ORCHESTRATOR ────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Google Drive Assets Migration Helper")
    parser.add_argument("--download-only", action="store_true", help="Only download folders from GDrive and exit.")
    parser.add_argument("--execute", action="store_true", help="Perform the actual GCS uploads and Firestore registering.")
    args = parser.parse_args()
    
    # 1. Fetch Auth Token
    token = get_gcloud_token()
    
    # 2. Download folders from Google Drive
    download_all_folders()
    if args.download_only:
        log_success("Download-only complete! Check '01_evolution/scratch/gdrive_imports/'.")
        return
        
    # 3. Retrieve Horse SSOT Records
    horses = fetch_registered_horses(token)
    
    # 4. Scan files and compile proposal list
    proposed_uploads = scan_files_and_map(horses)
    
    if not proposed_uploads:
        log_warning("No matching images or videos found to migrate.")
        return
        
    # 5. Display proposed map (Dry-Run Summary)
    print("\n" + "="*80)
    print(f" MIGRATION MAP PROPOSAL (Dry Run Mode) — Total Files Found: {len(proposed_uploads)}")
    print("="*80)
    for i, item in enumerate(proposed_uploads, 1):
        print(f" {i:02d}. File: {item['file_name']}")
        print(f"     Horse:    {item['horse_name']} (ID: {item['horse_id']})")
        print(f"     Date:     {item['date']}")
        print(f"     Category: {item['asset_category'].upper()}")
        print(f"     Tags:     [{item['tags']}]")
        print(f"     Alt:      \"{item['alt']}\"")
        print("-"*80)
        
    # 6. Execute uploads if flag is passed
    if args.execute:
        print("\n" + "#"*80)
        print(" EXECUTION STARTED ")
        print("#"*80)
        execute_uploads(proposed_uploads, token)
    else:
        print("\n\033[93m[NOTICE]\033[0m Run this script with '--execute' to perform the actual migration upload.")
        print("Example: python3 scratch/import_gdrive_assets.py --execute")

if __name__ == "__main__":
    main()
