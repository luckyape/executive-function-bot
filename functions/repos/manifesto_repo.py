from ..firestore_client import get_db

def get_manifesto_text(user_id: str) -> str:
    """
    Retrieves the manifesto text for a user.
    """
    db = get_db()
    doc_ref = db.collection("users").document(user_id)
    doc = doc_ref.get()
    if doc.exists:
        user_data = doc.to_dict()
        return user_data.get("manifesto", "No manifesto set.")
    return "No manifesto set."

def update_manifesto(user_id: str, new_manifesto: str) -> None:
    """
    Updates the manifesto for a user.
    """
    db = get_db()
    doc_ref = db.collection("users").document(user_id)
    doc_ref.set({"manifesto": new_manifesto}, merge=True)
