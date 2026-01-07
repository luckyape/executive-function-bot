import os
import datetime
from typing import List, Dict, Any, Optional
from google.cloud.firestore_v1.base_query import FieldFilter
from firestore_client import get_db

# NOTE: No global db initialization here!
# All functions must call get_db() to access Firestore.

def get_manifesto(user_id: str) -> str:
    """Returns the user's North Star goal (Manifesto)."""
    db = get_db()
    doc = db.collection("users").document(str(user_id)).get()
    if doc.exists:
        return doc.to_dict().get("manifesto", "No manifesto set.")
    return "No manifesto set."

def set_manifesto(user_id: str, manifesto: str) -> str:
    """Sets or updates the user's North Star goal."""
    db = get_db()
    db.collection("users").document(str(user_id)).set({
        "manifesto": manifesto,
        "updated_at": firestore.SERVER_TIMESTAMP
    }, merge=True)
    return "Manifesto updated."

# We need firestore module for SERVER_TIMESTAMP constants if we use them directly.
# However, `firestore.SERVER_TIMESTAMP` comes from `firebase_admin.firestore`.
# Importing it at top level is fine as it doesn't trigger auth.
from firebase_admin import firestore

def add_task(user_id: str, description: str) -> str:
    """Saves a new task to Firestore for the user."""
    db = get_db()
    task_ref = db.collection("users").document(str(user_id)).collection("tasks").document()
    task_ref.set({
        "description": description,
        "status": "pending",
        "created_at": firestore.SERVER_TIMESTAMP
    })
    return f"Task added: {description}"

def get_pending_tasks(user_id: str) -> List[Dict[str, Any]]:
    """Returns a list of incomplete tasks and saves their IDs for quick actions."""
    db = get_db()
    user_ref = db.collection("users").document(str(user_id))
    tasks_ref = user_ref.collection("tasks")
    # Order by creation time to ensure consistent numbering for the '#N' feature
    query = tasks_ref.where(filter=FieldFilter("status", "==", "pending")).order_by("created_at").stream()

    tasks = []
    task_ids = []
    for doc in query:
        data = doc.to_dict()
        data["id"] = doc.id
        task_ids.append(doc.id)
        # Convert timestamp to string for LLM readability
        if "created_at" in data and data["created_at"]:
            data["created_at"] = str(data["created_at"])
        tasks.append(data)

    # Save the IDs of the listed tasks for future reference by '#N' completion
    user_ref.set({"last_listed_tasks": task_ids}, merge=True)

    return tasks

def complete_task(user_id: str, query: Optional[str] = None) -> str:
    """
    Marks a task as done. Handles multiple scenarios:
    - If query is empty/None/'done' and there's only one task, it's completed.
    - If query is '#N', completes the Nth task from the last 'list' command.
    - Otherwise, fuzzy matches against task descriptions.
    """
    db = get_db()
    user_ref = db.collection("users").document(str(user_id))
    tasks_ref = user_ref.collection("tasks")

    pending_tasks_query = tasks_ref.where(filter=FieldFilter("status", "==", "pending")).order_by("created_at")
    pending_tasks = list(pending_tasks_query.stream())

    if not pending_tasks:
        return "You have no pending tasks to complete."

    # Normalize query for robustness, but keep original for messages
    original_query_str = query if query is not None else ""
    clean_query = query.strip().lower() if query else ""
    if clean_query.startswith("done"):
        clean_query = clean_query.removeprefix("done").strip()

    if not clean_query:
        if len(pending_tasks) == 1:
            task_to_complete = pending_tasks[0]
            task_to_complete.reference.update({"status": "done"})
            return f"Task marked as done: {task_to_complete.to_dict().get('description')}"
        else:
            return "You have multiple pending tasks. Please specify which one to complete (e.g., 'done #1' or 'done <task name>')."

    if clean_query.startswith("#"):
        try:
            index = int(clean_query[1:]) - 1
            user_doc = user_ref.get()
            if not user_doc.exists: return "Cannot find user data. Please 'list' tasks first."
            last_listed_ids = user_doc.to_dict().get("last_listed_tasks")
            if not last_listed_ids: return "You need to 'list' tasks before using the '#' shortcut."
            if 0 <= index < len(last_listed_ids):
                task_id = last_listed_ids[index]
                task_ref = tasks_ref.document(task_id)
                task_doc = task_ref.get()
                if task_doc.exists and task_doc.to_dict().get('status') == 'pending':
                    task_ref.update({"status": "done"})
                    return f"Task marked as done: {task_doc.to_dict().get('description')}"
                else:
                    return f"Task #{index+1} from your last list is already completed or cannot be found."
            else:
                return f"Invalid task number: #{index+1}. You have {len(last_listed_ids)} tasks in your last list."
        except (ValueError, IndexError):
            return "Invalid task number format. Please use '#1', '#2', etc."

    # Last resort: fuzzy match on the cleaned query
    matched_tasks = [p for p in pending_tasks if clean_query in p.to_dict().get("description", "").lower()]

    if len(matched_tasks) == 1:
        task_to_complete = matched_tasks[0]
        task_to_complete.reference.update({"status": "done"})
        return f"Task marked as done: {task_to_complete.to_dict().get('description')}"
    elif len(matched_tasks) > 1:
        descriptions = [f" - {d.to_dict().get('description')}" for d in matched_tasks]
        return f"Multiple tasks match your query '{original_query_str}'. Please be more specific:\n" + "\n".join(descriptions)
    else:
        return f"No pending task found matching '{original_query_str}'."

# Map of tool names to functions for easy execution
TOOL_MAP = {
    "get_manifesto": get_manifesto,
    "set_manifesto": set_manifesto,
    "add_task": add_task,
    "get_pending_tasks": get_pending_tasks,
    "complete_task": complete_task
}

# Definitions for Gemini
TOOL_DEFINITIONS = [
    {
        "name": "get_manifesto",
        "description": "Get the user's manifesto or 'North Star' goal.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "user_id": {"type": "STRING", "description": "The Telegram user ID"}
            },
            "required": ["user_id"]
        }
    },
    {
        "name": "set_manifesto",
        "description": "Set or update the user's manifesto or 'North Star' goal.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "user_id": {"type": "STRING", "description": "The Telegram user ID"},
                "manifesto": {"type": "STRING", "description": "The new manifesto content"}
            },
            "required": ["user_id", "manifesto"]
        }
    },
    {
        "name": "add_task",
        "description": "Add a new task to the user's list.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "user_id": {"type": "STRING", "description": "The Telegram user ID"},
                "description": {"type": "STRING", "description": "The task description"}
            },
            "required": ["user_id", "description"]
        }
    },
    {
        "name": "get_pending_tasks",
        "description": "Get a list of pending tasks for the user.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "user_id": {"type": "STRING", "description": "The Telegram user ID"}
            },
            "required": ["user_id"]
        }
    },
    {
        "name": "complete_task",
        "description": "Mark a task as completed. Can use a description fragment, '#N' from the last list, or complete the sole task if no query is provided.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "user_id": {"type": "STRING", "description": "The Telegram user ID"},
                "query": {"type": "STRING", "description": "The task identifier: a description fragment, '#N', or empty to complete the sole task."}
            },
            "required": ["user_id"]
        }
    }
]
