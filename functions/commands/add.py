from __future__ import annotations
from telegram_utils import send_message
from tools import add_task

def handle_add_command(context: dict) -> None:
    """
    Handles the /add command.
    """
    user_id = context["user_id"]
    chat_id = context["chat_id"]
    payload = context.get("payload", "")

    if not payload:
        send_message(chat_id, "Please provide a task to add. Usage: /add <task description>")
        return

    add_task(str(user_id), payload)
    send_message(chat_id, f"Task added: {payload}")
