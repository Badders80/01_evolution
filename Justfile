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

# Create Cloud Storage buckets (run once in US for free tier)
create-buckets:
    gcloud storage buckets create gs://evolution-horse-images --location=us-central1 || true
    gcloud storage buckets create gs://evolution-horse-docs --location=us-central1 || true
    gcloud storage buckets create gs://evolution-engine-speech-temp --location=us-central1 || true

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

# Run Email Ingest pipeline locally via Gmail API
run-email-ingest:
    python3 api/email-ingest/trigger_gmail.py

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

# ═══════════════════════════════════════════════════════════
# Storage Hygiene & Prevention Tooling
# ═══════════════════════════════════════════════════════════

# Validate storage contract (slug sync, microchip consistency, folder structure)
check-repo:
    @python3 tools/check_storage_sync.py --verbose

# Scaffold a new horse across both surfaces + HORSES.csv
new-horse slug microchip="":
    @echo "Scaffolding horse: {{slug}} (microchip: {{microchip}})"
    @mkdir -p ../_assets/horses/{{slug}}/images ../_assets/horses/{{slug}}/videos ../_assets/horses/{{slug}}/transcripts ../_assets/horses/{{slug}}/documents ../_assets/horses/{{slug}}/investor-updates
    @mkdir -p horses/{{slug}}
    @test -f horses/{{slug}}/profile.md || echo "---\nslug: {{slug}}\ntype: horse\nname: \nmicrochip: \"{{microchip}}\"\nstatus: active\nupdated_at: $(date +%Y-%m-%d)\n---\n\n# {{slug}}\n\n## At a Glance\n\n| Field | Value |\n|-------|-------|\n| Microchip | {{microchip}} |\n\n---\n\nProfile text here." > horses/{{slug}}/profile.md
    @test -f horses/{{slug}}/pedigree.json || echo '{\n  "microchip": "{{microchip}}",\n  "horse_slug": "{{slug}}",\n  "sire": "",\n  "dam": "",\n  "breeder": ""\n}' > horses/{{slug}}/pedigree.json
    @test -f horses/{{slug}}/race-record.json || echo '{\n  "microchip": "{{microchip}}",\n  "horse_slug": "{{slug}}",\n  "starts": []\n}' > horses/{{slug}}/race-record.json
    @echo "✅ Created both surfaces for {{slug}}"
    @echo "⚠️  Add entry to _assets/horses/HORSES.csv manually (or run: just sync-horses)"
    @echo "⚠️  Edit horses/{{slug}}/profile.md with horse details from loveracing.nz"

# Generate HORSES.csv from all profile.md frontmatter
sync-horses:
    @python3 tools/sync_horses.py

# Show asset coverage per horse (images, videos, transcripts, documents, updates)
coverage:
    @python3 tools/coverage_report.py

# Show a single-horse dashboard (profile, pedigree, assets, transcripts)
horse slug:
    @python3 tools/horse_dashboard.py {{slug}}

# Auto-generate transcript/update index markdown for a horse
index-horse slug:
    @python3 tools/index_horse.py {{slug}}

# Migrate updates from old platform folder (repeatable, safe to re-run)
migrate-updates:
    @python3 tools/migrate_updates.py --dry-run

# Migrate updates for real (copies files)
migrate-updates-run:
    @python3 tools/migrate_updates.py