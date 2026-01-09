from datetime import datetime
from firebase_admin import firestore
from firestore_client import db

class ScratchRepo:
    def __init__(self, user_id):
        if not user_id:
            raise ValueError("user_id must be provided")
        self.collection = db.collection(f'users/{user_id}/scratch')

    def add(self, text):
        """
        Adds a new scratch entry for the user.
        """
        doc_ref = self.collection.document()
        doc_ref.set({
            'text': text,
            'created_at': firestore.SERVER_TIMESTAMP
        })
        return doc_ref.id

    def get_all(self, limit=10):
        """
        Retrieves the latest N scratch entries for the user.
        """
        query = self.collection.order_by('created_at', direction=firestore.Query.DESCENDING).limit(limit)
        docs = query.stream()
        return [doc for doc in docs]

    def clear_all(self):
        """
        Deletes all scratch entries for a user.
        """
        docs = self.collection.stream()
        for doc in docs:
            doc.reference.delete()

    def get_by_id(self, scratch_id):
        """
        Retrieves a scratch entry by its ID.
        """
        doc_ref = self.collection.document(scratch_id)
        doc = doc_ref.get()
        if doc.exists:
            return doc
        return None
