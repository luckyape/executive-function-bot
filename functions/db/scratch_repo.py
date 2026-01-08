from datetime import datetime
from firebase_admin import firestore
from ..firestore_client import db

class ScratchRepo:
    def __init__(self):
        self.collection = db.collection('scratch')

    def add(self, user_id, text):
        """
        Adds a new scratch entry for the user.
        """
        doc_ref = self.collection.document()
        doc_ref.set({
            'user_id': user_id,
            'text': text,
            'created_at': firestore.SERVER_TIMESTAMP
        })
        return doc_ref.id

    def get_all(self, user_id, limit=10):
        """
        Retrieves the latest N scratch entries for the user.
        """
        query = self.collection.where('user_id', '==', user_id).order_by('created_at', direction=firestore.Query.DESCENDING).limit(limit)
        docs = query.stream()
        return [doc for doc in docs]

    def clear_all(self, user_id):
        """
        Deletes all scratch entries for a user.
        """
        query = self.collection.where('user_id', '==', user_id)
        docs = query.stream()
        for doc in docs:
            doc.reference.delete()

    def get_by_id(self, user_id, scratch_id):
        """
        Retrieves a scratch entry by its ID.
        """
        doc_ref = self.collection.document(scratch_id)
        doc = doc_ref.get()
        if doc.exists and doc.to_dict().get('user_id') == user_id:
            return doc
        return None
