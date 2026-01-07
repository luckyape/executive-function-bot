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
    """
    Returns a list of incomplete tasks.
    Crucially, it also saves the IDs of the *last listed* tasks to the user's
    document. This allows for completion by index (e.g., "done #1").
    """
    db = get_db()
    tasks_ref = db.collection("users").document(str(user_id)).collection("tasks")
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

    # Save the last listed task IDs for indexed completion
    db.collection("users").document(str(user_id)).set({
        "last_listed_tasks": task_ids
    }, merge=True)

    return tasks

def complete_task(user_id: str, query: str) -> str:
    """
    Marks a task as done. Handles:
    1. No query given: If only one task exists, completes it.
    2. '#<index>': Completes task by its 1-based index from the last `list` command.
    3. '<fragment>': Fuzzy-matches task by description.
    """
    db = get_db()
    user_ref = db.collection("users").document(user_id)
    tasks_ref = user_ref.collection("tasks")

    pending_tasks = get_pending_tasks(user_id) # This also refreshes last_listed_tasks

    # Case 1: No query, complete sole task
    if not query:
        if len(pending_tasks) == 1:
            task_id = pending_tasks[0]["id"]
            tasks_ref.document(task_id).update({"status": "done"})
            return f"Task marked as done: {pending_tasks[0]['description']}"
        elif len(pending_tasks) > 1:
            return "Multiple tasks pending. Please specify which one to complete (e.g., 'done #1' or 'done <keyword>')."
        else:
            return "No pending tasks to complete."

    # Case 2: Index-based completion
    if query.startswith("#") and query[1:].isdigit():
        try:
            index = int(query[1:]) - 1
            user_doc = user_ref.get()
            last_listed_ids = user_doc.to_dict().get("last_listed_tasks", [])

            if 0 <= index < len(last_listed_ids):
                task_id = last_listed_ids[index]
                task_doc = tasks_ref.document(task_id).get()
                if task_doc.exists:
                    tasks_ref.document(task_id).update({"status": "done"})
                    return f"Task marked as done: {task_doc.to_dict()['description']}"
                else:
                    return "Task not found (it may have been completed already)."
            else:
                return "Invalid task number."
        except Exception as e:
            return f"Error processing task number: {e}"

    # Case 3: Fuzzy text search
    # This is a simple substring match. More advanced fuzzy matching could be added.
    for task in pending_tasks:
        if query.lower() in task.get("description", "").lower():
            tasks_ref.document(task["id"]).update({"status": "done"})
            return f"Task marked as done: {task.get('description')}"

    return f"No pending task found matching '{query}'."

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
        "description": "Mark a task as completed. Can be identified by a description fragment, by its #index from the last list, or if it's the only task pending, no query is needed.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "user_id": {"type": "STRING", "description": "The Telegram user ID"},
                "query": {"type": "STRING", "description": "The task identifier (e.g., a keyword, '#1', or empty if only one task exists)."}
            },
            "required": ["user_id", "query"]
        }
    }
]
