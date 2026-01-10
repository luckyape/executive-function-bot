from __future__ import annotations

import logging
from functools import wraps
from typing import List, Dict, Any, Optional

from firebase_admin import firestore

from firestore_client import get_db
from audit.logger import log_tool_call, log_retrieval

from repos import manifesto_repo, tasks_repo
from db.scratch_repo import ScratchRepo

logger = logging.getLogger(__name__)


def tool_audit_decorator(func):
    """
    Decorator to log tool calls + results.
    Best-effort: never blocks the tool if logging fails.
    """
    @wraps(func)
    def wrapper(user_id: str, *args, **kwargs):
        tool_args: Dict[str, Any] = dict(kwargs)

        # Map positional args to parameter names (excluding user_id)
        try:
            arg_names = func.__code__.co_varnames[1:func.__code__.co_argcount]
            for i, arg in enumerate(args):
                if i < len(arg_names):
                    tool_args[arg_names[i]] = arg
        except Exception:
            pass

        result = func(user_id, *args, **kwargs)

        try:
            log_tool_call(user_id, func.__name__, tool_args, result)
        except Exception as e:
            logger.warning(f"log_tool_call failed for {func.__name__}: {e}", exc_info=True)

        return result

    return wrapper


@tool_audit_decorator
def get_manifesto(user_id: str) -> str:
    """Returns the user's North Star goal (Manifesto)."""
    return manifesto_repo.get_manifesto_text(user_id)


@tool_audit_decorator
def set_manifesto(user_id: str, manifesto: str) -> str:
    """Sets or updates the user's North Star goal."""
    manifesto_repo.update_manifesto(user_id, manifesto)
    return "Manifesto updated."


@tool_audit_decorator
def add_task(user_id: str, description: str) -> str:
    """Saves a new task for the user."""
    return tasks_repo.add_new_task(user_id, description)


@tool_audit_decorator
def get_pending_tasks(user_id: str) -> List[Dict[str, Any]]:
    """
    Returns a list of incomplete tasks.

    Best-effort extras:
      - cache last listed task IDs so UX can support '#N' completion reliably
      - log retrieval with the returned IDs
    """
    tasks = tasks_repo.get_user_pending_tasks(user_id) or []

    try:
        task_ids: List[str] = []
        for t in tasks:
            if isinstance(t, dict):
                tid = t.get("id")
                if tid:
                    task_ids.append(str(tid))

        if task_ids:
            db = get_db()
            user_ref = db.collection("users").document(str(user_id))
            user_ref.set(
                {
                    "last_listed_tasks": task_ids,
                    "last_listed_tasks_timestamp": firestore.SERVER_TIMESTAMP,
                },
                merge=True,
            )

            try:
                log_retrieval(user_id, "", task_ids, "pending_tasks")
            except Exception as e:
                logger.warning(f"log_retrieval failed for pending_tasks: {e}", exc_info=True)

    except Exception as e:
        logger.warning(f"Failed to cache last_listed_tasks for user {user_id}: {e}", exc_info=True)

    return tasks


@tool_audit_decorator
def complete_task(user_id: str, query: Optional[str] = None) -> str:
    """Marks a task as done."""
    return tasks_repo.complete_user_task(user_id, query)


@tool_audit_decorator
def recall(user_id: str, query: str) -> str:
    """
    Searches the user's archive for a given query.
    Returns a formatted string of the top results.
    """
    if not query or not query.strip():
        return "Please provide a search query."

    # Import locally to avoid cycles and avoid any global DB init
    from archive_repo import search_archive

    results = search_archive(user_id, query)
    if not results:
        return "No results found in your archive for that query."

    # Best-effort retrieval audit: log any IDs present
    try:
        ids: List[str] = []
        for r in results:
            if isinstance(r, dict):
                rid = r.get("id") or r.get("docId") or r.get("archiveId")
                if rid:
                    ids.append(str(rid))
        if ids:
            log_retrieval(user_id, query, ids, "archive_recall")
    except Exception as e:
        logger.warning(f"log_retrieval failed for recall: {e}", exc_info=True)

    formatted_results = ["From your archive:"]
    for res in results:
        title = res.get("title", "No title")
        updated_at = res.get("updatedAt", "No date")
        tags = ", ".join(res.get("tags", []))
        excerpt = res.get("summary", "No summary")

        formatted_results.append(
            f"- Title: {title}\n"
            f"  Updated: {updated_at}\n"
            f"  Tags: {tags}\n"
            f"  Excerpt: {excerpt}"
        )

    return "\n".join(formatted_results)


@tool_audit_decorator
def scratch(user_id: str, action: str, content: str = None) -> str:
    """
    Manages the scratchpad (quick notes).
    Actions: 'add', 'read', 'clear'.
    """
    repo = ScratchRepo(user_id)
    if action == "add":
        if not content:
            return "Content is required to add a note."
        scratch_id = repo.add(content)
        return f"Added note to scratchpad. ID: {scratch_id}"
    elif action == "read":
        entries = repo.get_all(limit=5)
        if not entries:
            return "Scratchpad is empty."
        return "\n".join([f"- {e.to_dict().get('text')}" for e in entries])
    elif action == "clear":
        repo.clear_all()
        return "Scratchpad cleared."
    return f"Unknown action: {action}"

@tool_audit_decorator
def archive(user_id: str, query: str) -> str:
    """
    Searches the user's archive for a given query.
    """
    return recall(user_id, query)

TOOL_MAP = {
    "get_manifesto": get_manifesto,
    "set_manifesto": set_manifesto,
    "add_task": add_task,
    "get_pending_tasks": get_pending_tasks,
    "complete_task": complete_task,
    "recall": recall,
    "scratch": scratch,
    "archive": archive,
}
