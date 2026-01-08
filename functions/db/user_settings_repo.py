from typing import Optional, Dict, Any
from enum import Enum
import logging

from firestore_client import get_db

logger = logging.getLogger(__name__)

class MemoryMode(Enum):
    OFF = "off"
    HOT = "hot"
    PROJECTS = "projects"
    STRICT = "strict"

def get_user_settings(user_id: str) -> Dict[str, Any]:
    """
    Retrieves a user's settings document.
    Defaults to 'strict' memory mode if not set.
    """
    db = get_db()
    doc_ref = db.collection("users").document(user_id)
    doc = doc_ref.get()

    if not doc.exists:
        # Default settings for a new user
        default_settings = {"memory_mode": MemoryMode.STRICT.value}
        try:
            doc_ref.set(default_settings, merge=True)
            return default_settings
        except Exception as e:
            logger.error(f"Failed to create default settings for user {user_id}: {e}")
            return {"memory_mode": MemoryMode.STRICT.value}

    user_data = doc.to_dict()
    # Ensure memory_mode exists, defaulting to 'strict'
    if "memory_mode" not in user_data:
        user_data["memory_mode"] = MemoryMode.STRICT.value
        try:
            doc_ref.set({"memory_mode": MemoryMode.STRICT.value}, merge=True)
        except Exception as e:
            logger.error(f"Failed to set default memory_mode for user {user_id}: {e}")

    return user_data

def set_memory_mode(user_id: str, mode: MemoryMode) -> bool:
    """
    Sets the memory mode for a user.
    """
    if not isinstance(mode, MemoryMode):
        raise ValueError("Invalid memory mode specified")

    db = get_db()
    doc_ref = db.collection("users").document(user_id)
    try:
        doc_ref.set({"memory_mode": mode.value}, merge=True)
        return True
    except Exception as e:
        logger.error(f"Failed to set memory mode for user {user_id}: {e}")
        return False

def get_memory_mode(user_id: str) -> MemoryMode:
    """
    Retrieves the memory mode for a user.
    """
    settings = get_user_settings(user_id)
    mode_str = settings.get("memory_mode", MemoryMode.STRICT.value)
    try:
        return MemoryMode(mode_str)
    except ValueError:
        logger.warning(f"Invalid memory mode '{mode_str}' for user {user_id}. Defaulting to 'strict'.")
        return MemoryMode.STRICT
