from __future__ import annotations

from telegram_utils import send_message
from tools import get_pending_tasks


def handle_list_command(context: dict) -> None:
    """
    Handles the /list command.
    """
    user_id = context["user_id"]
    chat_id = context["chat_id"]

    tasks = get_pending_tasks(str(user_id))
    if not tasks:
        send_message(chat_id, "You have no pending tasks. Use /add to create one.")
        return

    lines = []
    for t in tasks:
        idx = t.get("index")
        desc = t.get("description", "")
        if idx is not None:
            lines.append(f"#{idx} - {desc}")
        else:
            lines.append(f"- {desc}")

    response = "Your pending tasks:\n" + "\n".join(lines)
    send_message(chat_id, response)
