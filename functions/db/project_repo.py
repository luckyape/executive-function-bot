import datetime
from typing import List, Dict, Any, Optional

from google.cloud import firestore
from firestore_client import get_db


def create_project(user_id: str, name: str) -> Dict[str, Any]:
    """
    Creates a new project for a user.
    """
    db = get_db()
    user_ref = db.collection("users").document(user_id)
    projects_ref = user_ref.collection("projects")

    new_project_ref = projects_ref.document()
    project_id = new_project_ref.id

    project_data = {
        "id": project_id,
        "name": name,
        "goal": "",
        "currentState": "",
        "nextSteps": [],
        "constraints": [],
        "links": [],
        "lastTouchedAt": datetime.datetime.utcnow(),
        "isActive": True,
        "isArchived": False,
    }

    new_project_ref.set(project_data)
    user_ref.update({"activeProjectId": project_id})
    return project_data


def get_project(user_id: str, project_id: str) -> Optional[Dict[str, Any]]:
    """
    Retrieves a specific project for a user.
    """
    db = get_db()
    project_ref = db.collection("users").document(user_id).collection("projects").document(project_id)
    project = project_ref.get()
    return project.to_dict() if project.exists else None


def get_active_project(user_id: str) -> Optional[Dict[str, Any]]:
    """
    Retrieves the active project for a user.
    """
    db = get_db()
    user_ref = db.collection("users").document(user_id)
    user_data = user_ref.get().to_dict()

    if not user_data or "activeProjectId" not in user_data:
        return None

    project_id = user_data["activeProjectId"]
    return get_project(user_id, project_id)


def update_project(user_id: str, project_id: str, field: str, value: Any) -> None:
    """
    Updates a specific field of a project.
    """
    db = get_db()
    project_ref = db.collection("users").document(user_id).collection("projects").document(project_id)
    project_ref.update({field: value, "lastTouchedAt": datetime.datetime.utcnow()})


def close_project(user_id: str, project_id: str) -> None:
    """
    Closes a project by marking it as archived.
    """
    db = get_db()
    user_ref = db.collection("users").document(user_id)
    project_ref = user_ref.collection("projects").document(project_id)

    project_ref.update({"isActive": False, "isArchived": True})

    user_data = user_ref.get().to_dict()
    if user_data and user_data.get("activeProjectId") == project_id:
        user_ref.update({"activeProjectId": None})


def set_active_project(user_id: str, project_id: str) -> None:
    """
    Sets a project as the active project for a user.
    """
    db = get_db()
    user_ref = db.collection("users").document(user_id)
    user_ref.update({"activeProjectId": project_id})


def add_to_project_list_field(user_id: str, project_id: str, field: str, value: Any) -> None:
    """
    Adds an item to a list field of a project.
    """
    db = get_db()
    project_ref = db.collection("users").document(user_id).collection("projects").document(project_id)
    project_ref.update({field: firestore.ArrayUnion([value]), "lastTouchedAt": datetime.datetime.utcnow()})


def remove_from_project_list_field(user_id: str, project_id: str, field: str, value: Any) -> None:
    """
    Removes an item from a list field of a project.
    """
    db = get_db()
    project_ref = db.collection("users").document(user_id).collection("projects").document(project_id)
    project_ref.update({field: firestore.ArrayRemove([value]), "lastTouchedAt": datetime.datetime.utcnow()})
