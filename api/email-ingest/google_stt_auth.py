"""
google_stt_auth.py
Per-account Application Default Credentials for Google Speech-to-Text.

Work (alex@evolutionstables.nz) is primary; personal (baddeley0@gmail.com) is overflow.
Refresh tokens are stored separately so each account can be renewed independently.

Setup once:
    bash api/email-ingest/scripts/setup_google_stt_auth.sh
"""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Optional

from google.auth.transport.requests import Request
from google.cloud import speech, storage
from google.oauth2.credentials import Credentials

from account_switcher import Account

logger = logging.getLogger(__name__)

GCLOUD_DIR = Path.home() / ".config" / "gcloud"
ADC_WORK = Path(os.getenv("GOOGLE_ADC_WORK", GCLOUD_DIR / "adc_work.json"))
ADC_PERSONAL = Path(os.getenv("GOOGLE_ADC_PERSONAL", GCLOUD_DIR / "adc_personal.json"))
ADC_DEFAULT = GCLOUD_DIR / "application_default_credentials.json"
LEGACY_WORK_ADC = GCLOUD_DIR / "legacy_credentials" / "alex@evolutionstables.nz" / "adc.json"

SCOPES = ["https://www.googleapis.com/auth/cloud-platform"]
WORK_PROJECT = os.getenv("GOOGLE_CLOUD_PROJECT", "evolution-engine")
PERSONAL_PROJECT = os.getenv(
    "GOOGLE_STT_PERSONAL_PROJECT",
    "gen-lang-client-0838627804",
)
# Work evolution-engine billing is currently delinquent — use personal inline STT.
WORK_STT_ENABLED = os.getenv("GOOGLE_STT_WORK_ENABLED", "false").lower() == "true"

_ACCOUNT_ADC: dict[Account, Path] = {
    Account.WORK: ADC_WORK,
    Account.PERSONAL: ADC_PERSONAL,
}

_ACCOUNT_QUOTA: dict[Account, str] = {
    Account.WORK: "google_stt_work",
    Account.PERSONAL: "google_stt_personal",
}


def _candidate_adc_paths(account: Account) -> list[Path]:
    paths: list[Path] = [_ACCOUNT_ADC[account]]
    if account == Account.WORK:
        paths.extend([ADC_DEFAULT, LEGACY_WORK_ADC])
    return [path for path in paths if path.exists()]


def load_credentials(account: Account) -> Optional[Credentials]:
    """Load and refresh OAuth credentials for an account, if possible."""
    for path in _candidate_adc_paths(account):
        try:
            creds = Credentials.from_authorized_user_file(str(path), SCOPES)
            if creds.expired and creds.refresh_token:
                creds.refresh(Request())
            if creds.valid:
                logger.info("Loaded Google credentials for %s from %s", account.value, path)
                return creds
        except Exception as exc:
            logger.debug("ADC path %s not usable for %s: %s", path, account.value, exc)
    return None


def credentials_status() -> dict[str, dict]:
    """Human-readable credential health for CLI diagnostics."""
    from model_router import get_tracker

    tracker = get_tracker()
    status: dict[str, dict] = {}
    for account in (Account.WORK, Account.PERSONAL):
        creds = load_credentials(account)
        quota_id = _ACCOUNT_QUOTA[account]
        status[account.value] = {
            "email": "alex@evolutionstables.nz"
            if account == Account.WORK
            else "baddeley0@gmail.com",
            "adc_paths": [str(p) for p in _candidate_adc_paths(account)],
            "authenticated": creds is not None,
            "quota_rule": quota_id,
            "quota_remaining_seconds": tracker.remaining(quota_id),
            "project": WORK_PROJECT if account == Account.WORK else PERSONAL_PROJECT,
            "enabled": WORK_STT_ENABLED if account == Account.WORK else True,
            "transport": "gcs" if account == Account.WORK else "inline_chunks",
        }
    return status


def select_google_stt_account(duration_seconds: int = 60) -> Optional[Account]:
    """Pick an account with quota + credentials. Personal preferred while work billing is off."""
    from model_router import get_tracker

    tracker = get_tracker()
    order = (Account.WORK, Account.PERSONAL) if WORK_STT_ENABLED else (Account.PERSONAL, Account.WORK)
    for account in order:
        quota_id = _ACCOUNT_QUOTA[account]
        if not tracker.check(quota_id, amount=max(1, int(duration_seconds))):
            continue
        if load_credentials(account):
            return account
        logger.warning(
            "Google STT quota available on %s but credentials are missing/expired",
            account.value,
        )
    return None


def get_speech_client(account: Account) -> speech.SpeechClient:
    creds = load_credentials(account)
    if not creds:
        email = (
            "alex@evolutionstables.nz"
            if account == Account.WORK
            else "baddeley0@gmail.com"
        )
        raise RuntimeError(
            f"Google STT credentials for {email} are missing or expired. "
            "Run: bash api/email-ingest/scripts/setup_google_stt_auth.sh"
        )
    project = WORK_PROJECT if account == Account.WORK else PERSONAL_PROJECT
    return speech.SpeechClient(
        credentials=creds,
        client_options={"quota_project_id": project},
    )


def get_storage_client() -> storage.Client:
    """GCS uploads always use the work project bucket."""
    creds = load_credentials(Account.WORK)
    if creds:
        return storage.Client(project=WORK_PROJECT, credentials=creds)
    return storage.Client(project=WORK_PROJECT)