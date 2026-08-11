#!/usr/bin/env bash
# Refresh Google Speech-to-Text credentials for work + personal accounts.
#
# Run interactively in your WSL terminal (browser login required):
#   bash /home/evo/evo_01/01_evolution/api/email-ingest/scripts/setup_google_stt_auth.sh
#
# Stores:
#   ~/.config/gcloud/adc_work.json      → alex@evolutionstables.nz
#   ~/.config/gcloud/adc_personal.json  → baddeley0@gmail.com

set -euo pipefail

GCLOUD_DIR="$HOME/.config/gcloud"
ADC_WORK="$GCLOUD_DIR/adc_work.json"
ADC_PERSONAL="$GCLOUD_DIR/adc_personal.json"

WORK_EMAIL="alex@evolutionstables.nz"
PERSONAL_EMAIL="baddeley0@gmail.com"
PROJECT="${GOOGLE_CLOUD_PROJECT:-evolution-engine}"
PERSONAL_PROJECT="${GOOGLE_STT_PERSONAL_PROJECT:-gen-lang-client-0838627804}"

echo "=== Google STT dual-account setup ==="
echo "Work:     $WORK_EMAIL (project: $PROJECT)"
echo "Personal: $PERSONAL_EMAIL (overflow)"
echo

setup_account() {
  local email="$1"
  local outfile="$2"
  local label="$3"

  echo "--- $label ($email) ---"

  if ! gcloud auth list --format="value(account)" 2>/dev/null | grep -Fxq "$email"; then
    echo "Logging in $email (browser will open)..."
    gcloud auth login "$email"
  fi

  gcloud config set account "$email"
  gcloud config set project "$PROJECT"

  echo "Refreshing Application Default Credentials for $email..."
  gcloud auth application-default login

  cp "$GCLOUD_DIR/application_default_credentials.json" "$outfile"
  chmod 600 "$outfile"
  echo "[OK] Saved ADC → $outfile"
  echo
}

setup_account "$WORK_EMAIL" "$ADC_WORK" "WORK"
setup_account "$PERSONAL_EMAIL" "$ADC_PERSONAL" "PERSONAL"

echo "--- Enabling Speech API on personal project ($PERSONAL_PROJECT) ---"
gcloud services enable speech.googleapis.com \
  --project="$PERSONAL_PROJECT" \
  --account="$PERSONAL_EMAIL" 2>/dev/null || true
echo

# Restore work as default gcloud account
gcloud config set account "$WORK_EMAIL"
gcloud config set project "$PROJECT"

echo "=== Verifying credentials ==="
EVO_ROOT="$(cd "$(dirname "$0")/../../.." && pwd)"
if [ -f "$EVO_ROOT/.venv/bin/activate" ]; then
  # shellcheck disable=SC1091
  source "$EVO_ROOT/.venv/bin/activate"
else
  echo "[WARN] venv not found at $EVO_ROOT/.venv — using system python3"
fi

cd "$(dirname "$0")/.."
python3 transcribe.py --check-google-auth

echo
echo "[NOTE] Work project ($PROJECT) billing is currently delinquent."
echo "       Google STT uses personal account + project $PERSONAL_PROJECT by default."
echo "       Re-enable work billing and set GOOGLE_STT_WORK_ENABLED=true to restore work GCS path."
echo
echo "[DONE] Google STT auth ready."
echo "Re-run Kay transcripts with:"
echo "  cd $EVO_ROOT && source .venv/bin/activate && source ~/.env"
echo "  cd api/email-ingest"
echo "  python3 transcribe.py --dir /home/evo/Kay --speakers 2 --type interview --reconcile --engine auto"