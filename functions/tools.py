from __future__ import annotations

from typing import List, Dict, Any, Optional

from repos import manifesto_repo, tasks_repo


def get_manifesto(user_id: str) -> str:
    """Returns the user's North Star goal (Manifesto)."""
    return manifesto_repo.get_manifesto_text(user_id)


def set_manifesto(user_id: str, manifesto: str) -> str:
    """Sets or updates the user's North Star goal."""
    manifesto_repo.update_manifesto(user_id, manifesto)
    return "Manifesto updated."


def add_task(user_id: str, description: str) -> str:
    """Saves a new task for the user."""
    return tasks_repo.add_new_task(user_id, description)


def get_pending_tasks(user_id: str) -> List[Dict[str, Any]]:
    """Returns a list of incomplete tasks."""
    return tasks_repo.get_user_pending_tasks(user_id)


def complete_task(user_id: str, query: Optional[str] = None) -> str:
    """Marks a task as done."""
    return tasks_repo.complete_user_task(user_id, query)


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
        "description": "Search the user's archive and return the most relevant stored items.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "user_id": {"type": "STRING", "description": "The Telegram user ID"},
                "query": {"type": "STRING", "description": "Search query text"},
            },
            "required": ["user_id", "query"],
        },
    },
]