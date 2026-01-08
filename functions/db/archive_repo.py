from typing import List, Dict, Any, Optional
from firebase_admin import firestore
from functions.firestore_client import get_db

def search_archive(user_id: str, query: str) -> List[Dict[str, Any]]:
    """
    Performs a naive search against the user's archive.
    - Filters by documents where the 'tags' array contains the query.
    - A real implementation would also search a 'searchText' field.
    """
    db = get_db()
    user_ref = db.collection("users").document(str(user_id))
    archive_ref = user_ref.collection("archive")

    # Naive tag search
    tag_query = archive_ref.where("tags", "array_contains", query).stream()

    results = []
    for doc in tag_query:
        data = doc.to_dict()
        data["id"] = doc.id
        results.append(data)

    # In a real implementation, you would also perform a text search
    # and merge the results. For this first pass, we'll just use the tag query.

    return results
