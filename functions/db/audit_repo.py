from firebase_admin import firestore
from firestore_client import get_db

def save_audit_log(user_id: str, event_data: dict) -> None:
    """
    Saves an audit log entry to Firestore.

    Args:
        user_id: The ID of the user associated with the event.
        event_data: A dictionary containing the details of the event to be logged.
    """
    db = get_db()

    # Add a server timestamp to the event data
    event_data['timestamp'] = firestore.SERVER_TIMESTAMP

    # Save the audit log to a subcollection under the user's document
    db.collection('users').document(user_id).collection('audit_logs').add(event_data)
