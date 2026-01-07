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
    Returns a list of incomplete tasks, indexed numerically.
    It also saves the task IDs of this list for future reference.
    """
    db = get_db()
    user_ref = db.collection("users").document(str(user_id))
    tasks_ref = user_ref.collection("tasks")

    # Query pending tasks, ordering by creation date for consistent numbering
    query = tasks_ref.where(
        filter=FieldFilter("status", "==", "pending")
    ).order_by("created_at").stream()

    tasks = []
    task_ids = []
    for i, doc in enumerate(query):
        data = doc.to_dict()
        data["id"] = doc.id
        data["index"] = i + 1  # 1-based index for user display
        task_ids.append(doc.id)

        # Convert timestamp to string for LLM readability
        if "created_at" in data and data["created_at"]:
            data["created_at"] = str(data["created_at"])
        tasks.append(data)

    # Save the list of task IDs for the 'done #' command
    user_ref.set({"last_listed_tasks": task_ids}, merge=True)

    return tasks

def complete_task(user_id: str, query: str) -> str:
    """
    Marks a task as done based on a query which can be an index,
    a description fragment, or empty (for single-task completion).
    """
    db = get_db()
    user_ref = db.collection("users").document(str(user_id))
    tasks_ref = user_ref.collection("tasks")

    pending_tasks = get_pending_tasks(user_id) # This already orders them

    # Case 1: "done" or "mark my one task done" with a single pending task
    if not query or query.lower() == "mark my one task done":
        if len(pending_tasks) == 1:
            task_to_complete = pending_tasks[0]
            tasks_ref.document(task_to_complete["id"]).update({"status": "done"})
            return f"Task marked as done: {task_to_complete['description']}"
        elif len(pending_tasks) > 1:
            return "You have multiple tasks. Please specify which one to complete (e.g., 'done #1' or 'done <keyword>')."
        else:
            return "No pending tasks to complete."

    # Case 2: "done #1" - by index
    if query.startswith("#"):
        try:
            index = int(query[1:]) - 1 # 1-based to 0-based
            user_doc = user_ref.get()
            if user_doc.exists:
                last_listed_tasks = user_doc.to_dict().get("last_listed_tasks")
                if last_listed_tasks and 0 <= index < len(last_listed_tasks):
                    task_id = last_listed_tasks[index]
                    task_doc = tasks_ref.document(task_id).get()
                    if task_doc.exists:
                        description = task_doc.to_dict().get("description")
                        tasks_ref.document(task_id).update({"status": "done"})
                        return f"Task marked as done: {description}"
                    else:
                        return "That task number is no longer valid."
            return "Please 'list' tasks first to use numbered completion."
        except (ValueError, IndexError):
            return "Invalid task number."

    # Case 3: Fuzzy matching by description fragment
    matches = [
        task for task in pending_tasks
        if query.lower() in task.get("description", "").lower()
    ]

    if len(matches) == 1:
        match = matches[0]
        tasks_ref.document(match["id"]).update({"status": "done"})
        return f"Task marked as done: {match['description']}"
    elif len(matches) > 1:
        options = "\n".join([f"#{t['index']} - {t['description']}" for t in matches])
        return f"Ambiguous query. Which task did you mean?\n{options}"
    else:
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
        "description": "Mark a task as completed by its index (e.g., '#1'), a unique phrase from its description, or by saying 'done' if only one task is pending.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "user_id": {"type": "STRING", "description": "The Telegram user ID"},
                "query": {"type": "STRING", "description": "The index, phrase, or empty string to identify the task"}
            },
            "required": ["user_id", "query"]
        }
    }
]
