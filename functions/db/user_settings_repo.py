from typing import Optional
from ..firestore_client import get_db

DEFAULT_MEMORY_MODE = "projects"

def get_user_settings(user_id: str) -> dict:
    """
    Retrieves user settings from Firestore.
    """
    db = get_db()
    user_ref = db.collection("users").document(user_id)
    user_doc = user_ref.get()
    if user_doc.exists:
        return user_doc.to_dict().get("settings", {})
    return {}

def get_memory_mode(user_id: str) -> str:
    """
    Retrieves the memory mode for a user.
    Defaults to 'projects' if not set.
    """
    settings = get_user_settings(user_id)
    return settings.get("memory_mode", DEFAULT_MEMORY_MODE)

def set_memory_mode(user_id: str, mode: str) -> None:
    """
    Sets the memory mode for a user.
    """
    db = get_db()
    user_ref = db.collection("users").document(user_id)
    user_ref.set({"settings": {"memory_mode": mode}}, merge=True)
