import os
import firebase_admin
from firebase_admin import firestore
from firebase_admin import credentials

_db = None

def get_db():
    """
    Returns a lazily initialized Firestore client.
    Handles Emulator vs Production environments.
    """
    global _db
    if _db:
        return _db

    # Check if we are running in the emulator
    if os.environ.get("FIRESTORE_EMULATOR_HOST"):
        # Emulator mode: Use anonymous credentials
        if not firebase_admin._apps:
            # We need a project ID. Fallback to a dummy if not set.
            project_id = os.environ.get("GCLOUD_PROJECT") or os.environ.get("FIREBASE_PROJECT_ID") or "demo-project"
            cred = credentials.Anonymous()
            firebase_admin.initialize_app(cred, {"projectId": project_id})

        _db = firestore.client()
        print(f"Initialized Firestore (Emulator) for project: {os.environ.get('GCLOUD_PROJECT')}")
    else:
        # Production mode: Use ADC
        if not firebase_admin._apps:
            try:
                firebase_admin.get_app()
            except ValueError:
                firebase_admin.initialize_app()

        _db = firestore.client()

    return _db
