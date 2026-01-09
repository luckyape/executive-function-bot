from __future__ import annotations
from telegram_utils import send_message

def handle_recall_command(context: dict) -> None:
    """
    Handles the /recall command.
    """
    chat_id = context["chat_id"]
    send_message(chat_id, "The /recall command is not yet implemented.")
