from __future__ import annotations

import logging

from db.user_settings_repo import get_memory_mode, MemoryMode
from repos import manifesto_repo, tasks_repo

logger = logging.getLogger(__name__)


def build_context(user_id: str) -> str:
    """
    Builds the context string to be injected into the agent's prompt
    based on the user's memory mode.

    Modes:
      - OFF: no context
      - HOT: manifesto only
      - PROJECTS: manifesto + pending tasks
      - STRICT: manifesto + pending tasks (same as projects for now)

    Note: Project-card context was removed in this branch; if you reintroduce it,
    add it under PROJECTS/STRICT as another section.
    """
    try:
        mode = get_memory_mode(user_id)
    except Exception as e:
        logger.error(f"Failed to get memory mode for user {user_id}: {e}", exc_info=True)
        # Fail open, but deterministic: STRICT means "include what we can"
        mode = MemoryMode.STRICT

    if mode == MemoryMode.OFF:
        return ""

    context_parts: list[str] = []

    # HOT memory: Manifesto
    if mode in (MemoryMode.HOT, MemoryMode.PROJECTS, MemoryMode.STRICT):
        try:
            manifesto = manifesto_repo.get_manifesto_text(user_id)
            if manifesto and manifesto != "No manifesto set.":
                context_parts.append(f"## User Manifesto:\n{manifesto}")
        except Exception as e:
            logger.error(f"Failed to get manifesto for user {user_id}: {e}", exc_info=True)

    # PROJECTS memory: Pending Tasks
    if mode in (MemoryMode.PROJECTS, MemoryMode.STRICT):
        try:
            pending_tasks = tasks_repo.get_user_pending_tasks(user_id)
            if pending_tasks:
                task_list = "\n".join(
                    [f"- {t.get('description', 'No description')}" for t in pending_tasks]
                )
                context_parts.append(f"## Pending Tasks:\n{task_list}")
        except Exception as e:
            logger.error(f"Failed to get pending tasks for user {user_id}: {e}", exc_info=True)

    if not context_parts:
        return ""

    return "\n\n---\n\n".join(context_parts)