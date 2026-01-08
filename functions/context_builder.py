import logging
from .tools import get_manifesto, get_pending_tasks
from .db import project_repo, user_settings_repo

logger = logging.getLogger(__name__)

def build_context(user_id: str) -> str:
    """
    Builds the context for the agent based on the user's memory mode.
    """
    memory_mode = user_settings_repo.get_memory_mode(user_id)
    context_sources = []
    context = ""

    if memory_mode == "off":
        context_sources.append("none")
        context = "Memory is off."

    elif memory_mode == "hot":
        context_sources.append("manifesto")
        manifesto = get_manifesto(user_id)
        context = f"Manifesto: {manifesto}\n"

    elif memory_mode in ["projects", "strict"]:
        context_sources.append("manifesto")
        manifesto = get_manifesto(user_id)
        context = f"Manifesto: {manifesto}\n"

        context_sources.append("tasks")
        pending_tasks = get_pending_tasks(user_id)
        if pending_tasks:
            task_list = "\n".join([f"- {t['description']}" for t in pending_tasks])
            context += f"Pending Tasks:\n{task_list}\n"

        context_sources.append("project")
        active_project = project_repo.get_active_project(user_id)
        if active_project:
            context += f"Active Project:\n"
            for key, value in active_project.items():
                if key not in ["id", "isActive", "isArchived", "lastTouchedAt"]:
                    context += f"  {key}: {value}\n"

    logger.info(f"Context built for user {user_id} with mode '{memory_mode}'. Sources: {', '.join(context_sources)}")
    return context
