from typing import List, Dict, Any, Optional
import datetime
from firebase_admin import firestore
from google.cloud.firestore_v1.base_query import FieldFilter

from ..firestore_client import get_db

def add_new_task(user_id: str, description: str) -> str:
    """
    Saves a new task to Firestore for the user.
    """
    db = get_db()
    task_ref = db.collection("users").document(user_id).collection("tasks").document()
    task_ref.set(
        {
            "description": description,
            "status": "pending",
            "created_at": firestore.SERVER_TIMESTAMP,
        }
    )
    return f"Task added: {description}"

def get_user_pending_tasks(user_id: str) -> List[Dict[str, Any]]:
    """
    Returns a list of incomplete tasks and caches their IDs for quick actions.
    """
    db = get_db()
    user_ref = db.collection("users").document(user_id)
    tasks_ref = user_ref.collection("tasks")

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
        if "created_at" in data and data["created_at"]:
            data["created_at"] = str(data["created_at"])
        tasks.append(data)

    user_ref.set(
        {
            "last_listed_tasks": task_ids,
            "last_listed_tasks_timestamp": firestore.SERVER_TIMESTAMP,
        },
        merge=True,
    )
    return tasks

def complete_user_task(user_id: str, query: Optional[str] = None) -> str:
    """
    Marks a task as done based on a query.
    """
    db = get_db()
    user_ref = db.collection("users").document(user_id)
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

    if not clean_query:
        if len(pending_tasks) == 1:
            task_to_complete = pending_tasks[0]
            task_to_complete.reference.update({"status": "done"})
            return f"Task marked as done: {task_to_complete.to_dict().get('description')}"
        return "You have multiple pending tasks. Please specify which one to complete."

    if clean_query.startswith("#"):
        try:
            index = int(clean_query[1:]) - 1
            user_doc = user_ref.get()
            if not user_doc.exists:
                return "Please 'list' tasks first to use numbered completion."

            user_data = user_doc.to_dict() or {}
            last_listed_ids = user_data.get("last_listed_tasks") or []
            last_listed_ts = user_data.get("last_listed_tasks_timestamp")

            if last_listed_ts:
                now = datetime.datetime.now(datetime.timezone.utc)
                cache_age = now - last_listed_ts
                if cache_age.total_seconds() > 3600:
                    return "The task list is outdated. Please 'list' tasks first."

            if not last_listed_ids:
                return "You need to 'list' tasks before using the '#' shortcut."

            if index < 0 or index >= len(last_listed_ids):
                return f"Invalid task number: #{index + 1}."

            task_id = last_listed_ids[index]
            task_ref = tasks_ref.document(task_id)
            task_doc = task_ref.get()

            if not task_doc.exists:
                return "That task number is no longer valid."

            task_data = task_doc.to_dict() or {}
            if task_data.get("status") != "pending":
                return "That task is no longer pending."

            task_ref.update({"status": "done"})
            return f"Task marked as done: {task_data.get('description')}"

        except (ValueError, IndexError):
            return "Invalid task number format."

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
