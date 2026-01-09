from __future__ import annotations
from telegram_utils import send_message
from tools import complete_task

def handle_done_command(context: dict) -> None:
    """
    Handles the /done command.
    """
    user_id = context["user_id"]
    chat_id = context["chat_id"]
    payload = context.get("payload", "")

    if not payload:
        send_message(chat_id, "Please provide a task number or fragment to complete. Usage: /done <task # or fragment>")
        return

    result = complete_task(str(user_id), payload)
    send_message(chat_id, result)
