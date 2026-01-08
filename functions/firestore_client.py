"""
This module provides a client to interact with Google Cloud Firestore.

The Firestore database is structured as follows:

/users/{user_id} (document)
  - manifesto: "string"
  - updated_at: timestamp
  - last_listed_tasks: ["task_id_1", "task_id_2"]
  - last_listed_tasks_timestamp: timestamp
  - memory_mode: "hot" | "hot+projects" | "strict" | "off"

  /users/{user_id}/tasks (collection)
    - {task_id} (document)
      - description: "string"
      - status: "pending" | "done"
      - created_at: timestamp

  /users/{user_id}/memory_hot (collection)
    - {memory_id} (document)
      - content: "string"
      - created_at: timestamp
      - last_accessed_at: timestamp
      - source: "user" | "llm" | "promoted_scratchpad"

  /users/{user_id}/memory_scratchpad (collection)
    - {scratch_id} (document)
      - content: "string"
      - created_at: timestamp

  /users/{user_id}/memory_archive (collection)
    - {archive_id} (document)
      - content: "string"
      - created_at: timestamp
      - source: "user" | "llm"
      - original_id: "string" (from hot or scratch)

  /users/{user_id}/projects (collection)
    - {project_id} (document)
      - name: "string"
      - status: "active" | "archived"
      - created_at: timestamp
      /project_id/memories (collection)
        - {memory_id}
          - content: "string"
          - created_at: timestamp
"""

import os
from firebase_admin import firestore, initialize_app

_app = None

def get_db():
    """
    Returns a Firestore client, initializing the app if necessary.
    """
    global _app
    if not _app:
        # Check for emulator environment
        if os.getenv("FIRESTORE_EMULATOR_HOST"):
            # Use a dummy project ID for the emulator
            _app = initialize_app(options={"projectId": "demo-project"})
        else:
            _app = initialize_app()

    return firestore.client()
