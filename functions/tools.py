import datetime
from typing import List, Dict, Any, Optional

from google.cloud.firestore_v1.base_query import FieldFilter
from firebase_admin import firestore

from firestore_client import get_db
from functions.tools.recall import recall


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
    db.collection("users").document(str(user_id)).set(
        {"manifesto": manifesto, "updated_at": firestore.SERVER_TIMESTAMP},
        merge=True,
    )
    return "Manifesto updated."


def add_task(user_id: str, description: str) -> str:
    """Saves a new task to Firestore for the user."""
    db = get_db()
    task_ref = db.collection("users").document(str(user_id)).collection("tasks").document()
    task_ref.set(
        {
            "description": description,
            "status": "pending",
            "created_at": firestore.SERVER_TIMESTAMP,
        }
    )
    return f"Task added: {description}"


def get_pending_tasks(user_id: str) -> List[Dict[str, Any]]:
    """Returns a list of incomplete tasks and saves their IDs for quick actions."""
    db = get_db()
    user_ref = db.collection("users").document(str(user_id))
    tasks_ref = user_ref.collection("tasks")

    # Query pending tasks, ordering by creation date for consistent numbering
    query = (
        tasks_ref.where(filter=FieldFilter("status", "==", "pending"))
        .order_by("created_at")
        .stream()
    )

    tasks: List[Dict[str, Any]] = []
    task_ids: List[str] = []

    for doc in query:
        data = doc.to_dict() or {}
        data["id"] = doc.id
        task_ids.append(doc.id)

        # Convert timestamp to string for readability
        if "created_at" in data and data["created_at"]:
            data["created_at"] = str(data["created_at"])

        tasks.append(data)

    # Cache last listed IDs (and timestamp for staleness check)
    user_ref.set(
        {
            "last_listed_tasks": task_ids,
            "last_listed_tasks_timestamp": firestore.SERVER_TIMESTAMP,
        },
        merge=True,
    )

    return tasks


def complete_task(user_id: str, query: Optional[str] = None) -> str:
    """
    Marks a task as done.
    - If query is empty/None and there's only one task, it's completed.
    - If query is '#N', completes the Nth task from the last 'list' command.
    - Otherwise, fuzzy matches against task descriptions.
    """
    db = get_db()
    user_ref = db.collection("users").document(str(user_id))
    tasks_ref = user_ref.collection("tasks")

    pending_tasks_query = (
        tasks_ref.where(filter=FieldFilter("status", "==", "pending"))
        .order_by("created_at")
    )
    pending_tasks = list(pending_tasks_query.stream())

    if not pending_tasks:
        return "You have no pending tasks to complete."

    original_query_str = query if query is not None else ""
    clean_query = query.strip().lower() if query else ""
    if clean_query.startswith("done"):
        clean_query = clean_query.removeprefix("done").strip()

    # No query: complete sole task or ask to specify
    if not clean_query:
        if len(pending_tasks) == 1:
            task_to_complete = pending_tasks[0]
            task_to_complete.reference.update({"status": "done"})
            return f"Task marked as done: {task_to_complete.to_dict().get('description')}"
        return "You have multiple pending tasks. Please specify which one to complete (e.g., 'done #1' or 'done <task name>')."

    # '#N' completion path (uses cached list)
    if clean_query.startswith("#"):
        try:
            index = int(clean_query[1:]) - 1
            user_doc = user_ref.get()
            if not user_doc.exists:
                return "Please 'list' tasks first to use numbered completion."

            user_data = user_doc.to_dict() or {}
            last_listed_ids = user_data.get("last_listed_tasks") or []
            last_listed_ts = user_data.get("last_listed_tasks_timestamp")

            # Optional staleness check (1 hour)
            if last_listed_ts:
                now = datetime.datetime.now(datetime.timezone.utc)
                cache_age = now - last_listed_ts
                if cache_age.total_seconds() > 3600:
                    return "The task list is outdated. Please 'list' tasks first to see current tasks."

            if not last_listed_ids:
                return "You need to 'list' tasks before using the '#' shortcut."

            if index < 0 or index >= len(last_listed_ids):
                return f"Invalid task number: #{index+1}. You have {len(last_listed_ids)} tasks in your last list."

            task_id = last_listed_ids[index]
            task_ref = tasks_ref.document(task_id)
            task_doc = task_ref.get()

            if not task_doc.exists:
                return "That task number is no longer valid."

            task_data = task_doc.to_dict() or {}
            if task_data.get("status") != "pending":
                return "That task is no longer pending. Please 'list' tasks to see your current pending tasks."

            task_ref.update({"status": "done"})
            return f"Task marked as done: {task_data.get('description')}"

        except (ValueError, IndexError):
            return "Invalid task number format. Please use '#1', '#2', etc."

    # Fuzzy match on description
    matched = [
        p for p in pending_tasks
        if clean_query in (p.to_dict().get("description", "") or "").lower()
    ]

    if len(matched) == 1:
        task_to_complete = matched[0]
        task_to_complete.reference.update({"status": "done"})
        return f"Task marked as done: {task_to_complete.to_dict().get('description')}"
    if len(matched) > 1:
        descriptions = [f" - {d.to_dict().get('description')}" for d in matched]
        return (
            f"Multiple tasks match your query '{original_query_str}'. Please be more specific:\n"
            + "\n".join(descriptions)
        )
    return f"No pending task found matching '{original_query_str}'."


# Map of tool names to functions for easy execution
TOOL_MAP = {
    "get_manifesto": get_manifesto,
    "set_manifesto": set_manifesto,
    "add_task": add_task,
    "get_pending_tasks": get_pending_tasks,
    "complete_task": complete_task,
    "recall": recall,
}

# Definitions for Gemini
TOOL_DEFINITIONS = [
    {
        "name": "get_manifesto",
        "description": "Get the user's manifesto or 'North Star' goal.",
        "parameters": {
            "type": "OBJECT",
            "properties": {"user_id": {"type": "STRING", "description": "The Telegram user ID"}},
            "required": ["user_id"],
        },
    },
    {
        "name": "set_manifesto",
        "description": "Set or update the user's manifesto or 'North Star' goal.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "user_id": {"type": "STRING", "description": "The Telegram user ID"},
                "manifesto": {"type": "STRING", "description": "The new manifesto content"},
            },
            "required": ["user_id", "manifesto"],
        },
    },
    {
        "name": "add_task",
        "description": "Add a new task to the user's list.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "user_id": {"type": "STRING", "description": "The Telegram user ID"},
                "description": {"type": "STRING", "description": "The task description"},
            },
            "required": ["user_id", "description"],
        },
    },
    {
        "name": "get_pending_tasks",
        "description": "Get a list of pending tasks for the user.",
        "parameters": {
            "type": "OBJECT",
            "properties": {"user_id": {"type": "STRING", "description": "The Telegram user ID"}},
            "required": ["user_id"],
        },
    },
    {
        "name": "complete_task",
        "description": "Mark a task as completed. Can use a description fragment, '#N' from the last list, or empty to complete the sole task.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "user_id": {"type": "STRING", "description": "The Telegram user ID"},
                "query": {"type": "STRING", "description": "The task identifier: description fragment, '#N', or empty."},
            },
            "required": ["user_id"],
        },
    },
    {
        "name": "recall",
        "description": "Search the user's private archive of documents and notes.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "user_id": {"type": "STRING", "description": "The Telegram user ID"},
                "query": {"type": "STRING", "description": "The search query"},
            },
            "required": ["user_id", "query"],
        },
    },
]
