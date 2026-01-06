import os
import datetime
from typing import List, Dict, Any, Optional
import firebase_admin
from firebase_admin import firestore
from google.cloud.firestore_v1.base_query import FieldFilter

# Initialize Firebase Admin if not already initialized
# Note: In Cloud Functions, this is usually done in main.py, but we need the client here.
# We'll assume it's initialized in main.py before tools are called, OR check here.
try:
    firebase_admin.get_app()
except ValueError:
    firebase_admin.initialize_app()

db = firestore.client()

def get_manifesto(user_id: str) -> str:
    """Returns the user's North Star goal (Manifesto)."""
    doc = db.collection("users").document(str(user_id)).get()
    if doc.exists:
        return doc.to_dict().get("manifesto", "No manifesto set.")
    return "No manifesto set."

def set_manifesto(user_id: str, manifesto: str) -> str:
    """Sets or updates the user's North Star goal."""
    db.collection("users").document(str(user_id)).set({
        "manifesto": manifesto,
        "updated_at": firestore.SERVER_TIMESTAMP
    }, merge=True)
    return "Manifesto updated."

def add_task(user_id: str, description: str) -> str:
    """Saves a new task to Firestore for the user."""
    task_ref = db.collection("users").document(str(user_id)).collection("tasks").document()
    task_ref.set({
        "description": description,
        "status": "pending",
        "created_at": firestore.SERVER_TIMESTAMP
    })
    return f"Task added: {description}"

def get_pending_tasks(user_id: str) -> List[Dict[str, Any]]:
    """Returns a list of incomplete tasks."""
    tasks_ref = db.collection("users").document(str(user_id)).collection("tasks")
    query = tasks_ref.where(filter=FieldFilter("status", "==", "pending")).stream()

    tasks = []
    for doc in query:
        data = doc.to_dict()
        data["id"] = doc.id
        # Convert timestamp to string for LLM readability
        if "created_at" in data and data["created_at"]:
            data["created_at"] = str(data["created_at"])
        tasks.append(data)
    return tasks

def complete_task(user_id: str, task_description_fragment: str) -> str:
    """Marks a task as done based on a description fragment."""
    # Since LLM might not know ID, we search by description.
    tasks_ref = db.collection("users").document(str(user_id)).collection("tasks")
    query = tasks_ref.where(filter=FieldFilter("status", "==", "pending")).stream()

    for doc in query:
        data = doc.to_dict()
        if task_description_fragment.lower() in data.get("description", "").lower():
            doc.reference.update({"status": "done"})
            return f"Task marked as done: {data.get('description')}"

    return f"No pending task found matching '{task_description_fragment}'."

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
        "description": "Mark a task as completed by matching a part of its description.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "user_id": {"type": "STRING", "description": "The Telegram user ID"},
                "task_description_fragment": {"type": "STRING", "description": "A unique phrase from the task description to identify it"}
            },
            "required": ["user_id", "task_description_fragment"]
        }
    }
]
