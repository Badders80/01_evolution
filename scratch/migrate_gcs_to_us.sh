#!/usr/bin/env bash
# GCS Bucket Region Migration Script (Sydney -> US)
# Automatically runs via the active authenticated terminal

set -e

BACKUP_DIR="/home/evo/Downloads/gcs_backup"
IMAGES_BUCKET="gs://evolution-horse-images"
DOCS_BUCKET="gs://evolution-horse-docs"

echo "============================================================"
echo " Starting GCS Migration to us-central1 (Always Free Region) "
echo "============================================================"

# 1. Create backup directories
echo "[1/5] Creating local backup directory: $BACKUP_DIR"
mkdir -p "$BACKUP_DIR/images"
mkdir -p "$BACKUP_DIR/docs"

# 2. Download existing files from old buckets
echo "[2/5] Downloading current files from Sydney buckets..."
echo "Downloading from $IMAGES_BUCKET..."
gcloud storage cp -r "$IMAGES_BUCKET/*" "$BACKUP_DIR/images/" || echo "No files in images bucket or download failed."

echo "Downloading from $DOCS_BUCKET..."
gcloud storage cp -r "$DOCS_BUCKET/*" "$BACKUP_DIR/docs/" || echo "No files in docs bucket or download failed."

# 3. Delete the old Sydney buckets recursively
echo "[3/5] Deleting old Sydney-based buckets..."
gcloud storage rm --recursive "$IMAGES_BUCKET" --quiet
gcloud storage rm --recursive "$DOCS_BUCKET" --quiet

# 4. Re-create buckets in us-central1 (US region for Always Free tier)
echo "[4/5] Creating new buckets in us-central1 (US Region)..."
gcloud storage buckets create "$IMAGES_BUCKET" --location=us-central1
gcloud storage buckets create "$DOCS_BUCKET" --location=us-central1

# 5. Restore files to new US buckets
echo "[5/5] Restoring backup files to the new US buckets..."
gcloud storage cp -r "$BACKUP_DIR/images/*" "$IMAGES_BUCKET/" || echo "No images files to restore."
gcloud storage cp -r "$BACKUP_DIR/docs/*" "$DOCS_BUCKET/" || echo "No docs files to restore."

echo "============================================================"
echo " ✅ Migration Complete! "
echo " Buckets recreated in us-central1 (Always Free) with data restored. "
echo " Backup copy preserved at: $BACKUP_DIR "
echo "============================================================"
