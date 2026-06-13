# Evolution — Build Commands

set shell := ["bash", "-cu"]

# Default: show available commands
default:
    @just --list

# ─── API ──────────────────────────────────────────────────────────────────────

# Run SSOT API locally
run-ssot:
    cd api/ssot && functions-framework --target=ssot --port=8080

# Run Assets API locally
run-assets:
    cd api/assets && functions-framework --target=assets --port=8081

# Run KYC API locally
run-kyc:
    cd api/kyc && functions-framework --target=kyc --port=8082

# Run all API tests
test-api:
    cd api && pytest -v

# Run SSOT tests only
test-ssot:
    cd api && pytest ssot/tests/ -v

# Run Assets tests only
test-assets:
    cd api && pytest assets/tests/ -v

# Run KYC tests only
test-kyc:
    cd api && pytest kyc/tests/ -v

# ─── Infrastructure ────────────────────────────────────────────────────────────

# Create Firestore database (run once)
create-firestore:
    gcloud firestore databases create --region=australia-southeast1

# Create Cloud Storage buckets (run once)
create-buckets:
    gsutil mb gs://evolution-horse-images
    gsutil mb gs://evolution-horse-docs

# Deploy SSOT function
deploy-ssot:
    cp -r api/core api/ssot/core
    cd api/ssot && gcloud functions deploy ssot \
        --runtime python312 \
        --trigger-http \
        --region australia-southeast1 \
        --set-env-vars "ALLOWED_ORIGINS=https://evolutionstables.nz,https://evolution.2.0.vercel.app,https://02website-pearl.vercel.app" \
        --source . \
        --entry-point ssot

# Deploy Assets function
deploy-assets:
    cp -r api/core api/assets/core
    cd api/assets && gcloud functions deploy assets \
        --runtime python312 \
        --trigger-http \
        --region australia-southeast1 \
        --memory 512MB \
        --env-vars-file /tmp/env_vars.yaml \
        --source . \
        --entry-point assets

# Deploy KYC function
deploy-kyc:
    cp -r api/core api/kyc/core
    cd api/kyc && gcloud functions deploy kyc \
        --runtime python312 \
        --trigger-http \
        --region australia-southeast1 \
        --env-vars-file /tmp/env_vars.yaml \
        --source . \
        --entry-point kyc

# Run Racing Data API locally
run-racing-data:
    cd api/racing-data && functions-framework --target=racing-data --port=8083

# Deploy Racing Data function
deploy-racing-data:
    cd api/racing-data && gcloud functions deploy racing-data \
        --runtime python312 \
        --trigger-http \
        --allow-unauthenticated \
        --region australia-southeast1 \
        --memory 512MB \
        --entry-point racing_data

# Deploy Email Ingest function
deploy-email-ingest:
    cd api/email-ingest && gcloud functions deploy email-ingest \
        --runtime python312 \
        --trigger-http \
        --entry-point email_ingest \
        --region australia-southeast1 \
        --memory 512MB \
        --timeout 540s \
        --set-env-vars SSOT_API_URL=https://australia-southeast1-evolution-engine.cloudfunctions.net/ssot,ASSETS_API_URL=https://australia-southeast1-evolution-engine.cloudfunctions.net/assets

# Set up Cloud Scheduler for email ingest (twice daily: 09:00, 21:00 NZST)
setup-email-scheduler:
    gcloud scheduler jobs create http email-ingest-morning \
        --schedule="0 9 * * *" \
        --time-zone="Pacific/Auckland" \
        --uri="https://australia-southeast1-evolution-engine.cloudfunctions.net/email-ingest" \
        --http-method=POST \
        --location=australia-southeast1 \
        --oidc-service-account-email=evolution-engine@appspot.gserviceaccount.com
    gcloud scheduler jobs create http email-ingest-evening \
        --schedule="0 21 * * *" \
        --time-zone="Pacific/Auckland" \
        --uri="https://australia-southeast1-evolution-engine.cloudfunctions.net/email-ingest" \
        --http-method=POST \
        --location=australia-southeast1 \
        --oidc-service-account-email=evolution-engine@appspot.gserviceaccount.com

# ─── Full Check ────────────────────────────────────────────────────────────────

# Run all checks
check:
    @echo "🔍 Running Evolution checks..."
    @echo "  → API tests..."
    cd api && pytest -v
    @echo "  → App type-check..."
    cd app && npx tsc --noEmit
    @echo "  → App build..."
    cd app && npm run build
    @echo "✅ All checks passed"

# Clean build artifacts
clean:
    rm -rf app/.next app/dist
    find api -type d -name __pycache__ -exec rm -rf {} +

# ═══════════════════════════════════════════════════════════
# Task Master
# ═══════════════════════════════════════════════════════════

# List all tasks
task-list:
    @python3 ../_taskmaster/task_list.py

# Show the next ready task
task-next:
    @python3 ../_taskmaster/task_next.py

# Show task details
task-show id:
    @python3 ../_taskmaster/task_show.py {{id}}

# Mark task as in-progress
task-start id:
    @python3 ../_taskmaster/task_start.py {{id}}

# Mark task as done
task-done id:
    @python3 ../_taskmaster/task_done.py {{id}}

# Create a sprint markdown file from task IDs
sprint-start name *tasks:
    @python3 ../_taskmaster/sprint_start.py "--tasks={{tasks}}" "{{name}}"

# Launch the interactive Dev Portal and Control Tower
task-web:
    @python3 ../_taskmaster/server.py