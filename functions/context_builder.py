from .tools import get_manifesto, get_pending_tasks
from .db import project_repo


def build_context(user_id: str) -> str:
    """
    Builds the context for the agent, including manifesto, tasks, and active project.
    """
    manifesto = get_manifesto(user_id)
    pending_tasks = get_pending_tasks(user_id)
    active_project = project_repo.get_active_project(user_id)

    context = f"User ID: {user_id}\n"
    context += f"Manifesto: {manifesto}\n"

    if pending_tasks:
        task_list = "\n".join([f"- {t['description']}" for t in pending_tasks])
        context += f"Pending Tasks:\n{task_list}\n"

    if active_project:
        context += f"Active Project:\n"
        for key, value in active_project.items():
            context += f"  {key}: {value}\n"

    return context
