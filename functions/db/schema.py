# functions/db/schema.py

"""
Firestore schema for memory tiers.

This file defines the data structures for the different memory tiers in Firestore.

Collections:
- users/{userId}/hot_memory/{id}
- users/{userId}/scratch/{id}
- users/{userId}/archive/{id}
"""

# Required fields for every document in the memory collections
MEMORY_DOCUMENT_SCHEMA = {
    "createdAt": "timestamp",   # Server timestamp
    "updatedAt": "timestamp",   # Server timestamp
    "source": "string",         # 'explicit', 'repeated', or 'inferred'
    "confidence": "number",     # 0.0 to 1.0
    "ttlDays": "number",        # Optional: Time to live in days
    "expiresAt": "timestamp",   # Optional: Calculated as createdAt + ttlDays
    "tags": "array",            # Array of strings
    "projectId": "string",      # Optional
}

# Defaults
# - Scratch memory defaults to a short TTL (e.g., 7-14 days).
# - Archive memory defaults to no TTL unless explicitly set.
# - Hot memory has no default TTL.
