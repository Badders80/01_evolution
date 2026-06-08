"""
account_switcher.py
Handles auth context switching between work (alex@evolutionstables.nz)
and personal (baddeley0@gmail.com) Google accounts for quota-aware routing.

Usage:
    from account_switcher import use_account, Account
    with use_account(Account.PERSONAL):
        # Calls here use baddeley0@gmail.com credentials
        result = model_router.get_router().aistudio_chat("...")
"""
import os
import logging
import subprocess
from enum import Enum
from contextlib import contextmanager
from typing import Optional

logger = logging.getLogger(__name__)

class Account(Enum):
    WORK = "work"           # alex@evolutionstables.nz  — GCP project evolution-engine
    PERSONAL = "personal"   # baddeley0@gmail.com       — AI Studio free tier

# Map accounts to their active gcloud credentials
_ACCOUNT_GCLOUD = {
    Account.WORK: "alex@evolutionstables.nz",
    Account.PERSONAL: "baddeley0@gmail.com",
}

# Map accounts to their AI Studio / API keys
_ACCOUNT_KEYS = {
    Account.WORK: os.getenv("GEMINI_API_KEY", ""),        # rarely used, gated
    Account.PERSONAL: os.getenv("AI_STUDIO_API_KEY", ""), # free tier
}

# Track which account is active so other modules can read it
_active_account: Optional[Account] = None

def get_active_account() -> Optional[Account]:
    return _active_account

def _gcloud_set_account(email: str) -> bool:
    """Switch gcloud active account. Returns True if successful."""
    try:
        result = subprocess.run(
            ["gcloud", "config", "set", "account", email],
            capture_output=True, text=True, timeout=15
        )
        if result.returncode == 0:
            logger.info(f"Switched gcloud account to {email}")
            return True
        else:
            logger.warning(f"gcloud switch failed: {result.stderr}")
            return False
    except Exception as e:
        logger.warning(f"gcloud subprocess error: {e}")
        return False

def _gcloud_current_account() -> str:
    """Return currently active gcloud account email."""
    try:
        result = subprocess.run(
            ["gcloud", "config", "get-value", "account"],
            capture_output=True, text=True, timeout=10
        )
        return result.stdout.strip()
    except Exception:
        return ""

@contextmanager
def use_account(account: Account):
    """
    Context manager that switches gcloud + environment to the requested account.
    Restores previous account on exit.
    """
    global _active_account
    prev_account = _active_account
    prev_email = _gcloud_current_account()
    target_email = _ACCOUNT_GCLOUD.get(account, "")
    key = _ACCOUNT_KEYS.get(account, "")

    # Set environment key for this account
    if account == Account.PERSONAL:
        os.environ["AI_STUDIO_API_KEY"] = key
    elif account == Account.WORK:
        os.environ["GEMINI_API_KEY"] = key

    # Switch gcloud if needed
    if target_email and prev_email != target_email:
        _gcloud_set_account(target_email)

    _active_account = account
    logger.info(f"Account context set to {account.value} ({target_email})")
    try:
        yield account
    finally:
        _active_account = prev_account
        if prev_email and _gcloud_current_account() != prev_email:
            _gcloud_set_account(prev_email)
        logger.info(f"Account context restored to {prev_account.value if prev_account else 'previous'}")

def ensure_personal_for_aistudio():
    """
    Convenience: if not already on personal account, switch to it.
    Use before any AI Studio call to guarantee free-tier billing.
    """
    if _active_account != Account.PERSONAL:
        logger.info("Auto-switching to personal account for AI Studio free tier")
        _gcloud_set_account(_ACCOUNT_GCLOUD[Account.PERSONAL])
        os.environ["AI_STUDIO_API_KEY"] = _ACCOUNT_KEYS[Account.PERSONAL]
        _active_account = Account.PERSONAL
