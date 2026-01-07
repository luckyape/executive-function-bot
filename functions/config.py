import os
import json
import logging

logger = logging.getLogger(__name__)

def get_config(key: str, default: str = None) -> str:
    """
    Retrieves configuration values.
    Prioritizes:
    1. Standard Environment Variables (e.g., TELEGRAM_TOKEN)
    2. Lowercase/Dot notation variants mapped to env vars (e.g. telegram_token)

    Note: 'firebase functions:config:set' (legacy) does not automatically populate
    os.environ in Python Cloud Functions Gen 2 without extra steps.
    We recommend setting environment variables directly via 'firebase functions:secrets:set'
    or inside firebase.json / .env files for Gen 2.
    """
    # 1. Try exact upper case key (Standard)
    val = os.environ.get(key.upper())
    if val:
        return val

    # 2. Try legacy mapping (telegram.token -> TELEGRAM_TOKEN)
    normalized_key = key.replace('.', '_').upper()
    val = os.environ.get(normalized_key)
    if val:
        return val

    # 3. Try exact key as passed
    val = os.environ.get(key)
    if val:
        return val

    # 4. Try lowercase key (e.g. telegram_token)
    val = os.environ.get(key.replace('.', '_').lower())
    if val:
        return val

    if default is not None:
        return default

    # Log warning if critical keys are missing
    logger.warning(f"Config key '{key}' not found in environment variables.")
    return None

def is_safe_mode() -> bool:
    """Checks if the app is in Panic Safe Mode."""
    val = get_config("APP_SAFE_MODE", "false").lower()
    return val in ["true", "1", "yes", "on"]
