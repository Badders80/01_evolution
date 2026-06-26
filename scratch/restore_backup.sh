#!/usr/bin/env bash
# GCS Bucket Restore Script
set -e

BACKUP_DIR="/home/evo/Downloads/gcs_backup"

echo "=========================================="
echo " Restoring GCS files from local backup... "
echo "=========================================="

if [ -d "$BACKUP_DIR/images/horse" ]; then
    echo "Uploading images to gs://evolution-horse-images/..."
    gcloud storage cp -r "$BACKUP_DIR/images/horse" gs://evolution-horse-images/
else
    echo "No horse images found in backup."
fi

if [ -d "$BACKUP_DIR/docs/horse" ]; then
    echo "Uploading documents/videos to gs://evolution-horse-docs/..."
    gcloud storage cp -r "$BACKUP_DIR/docs/horse" gs://evolution-horse-docs/
else
    echo "No horse documents/videos found in backup."
fi

echo "=========================================="
echo " ✅ Restore Complete! "
echo "=========================================="
