import os
import json
import logging

logger = logging.getLogger(__name__)

def _parse_runtime_config(key: str) -> str:
    """
    Attempts to parse the legacy CLOUD_RUNTIME_CONFIG JSON blob.
    Expected format: {"telegram": {"token": "..."}}
    """
    config_str = os.environ.get("CLOUD_RUNTIME_CONFIG")
    if not config_str:
        return None

    try:
        config = json.loads(config_str)
        # Handle flattened keys if necessary, but typically it is nested
        # key input: "TELEGRAM_TOKEN" -> we look for "telegram" -> "token"
        if key == "TELEGRAM_TOKEN":
            return config.get("telegram", {}).get("token")
        elif key == "OPENAI_API_KEY":
            return config.get("openai", {}).get("key")
    except Exception as e:
        logger.warning(f"Failed to parse CLOUD_RUNTIME_CONFIG: {e}")

    return None

def get_config(key: str, default: str = None) -> str:
    """
    Retrieves configuration values.
    Prioritizes:
    1. Standard Environment Variables (e.g., TELEGRAM_TOKEN)
    2. Lowercase/Dot notation variants mapped to env vars (e.g. telegram_token)
    3. Legacy CLOUD_RUNTIME_CONFIG (fallback)
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

    # 5. Fallback: Legacy Runtime Config
    val = _parse_runtime_config(normalized_key)
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
