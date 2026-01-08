# functions/tools/__init__.py

from repos.manifesto_repo import get_manifesto, set_manifesto
from repos.tasks_repo import add_task, get_pending_tasks, complete_task

# If Agent expects these too, export them here as well (adjust if your names differ)
from tools.tool_map import TOOL_MAP, TOOL_DEFINITIONS  # or wherever they live
