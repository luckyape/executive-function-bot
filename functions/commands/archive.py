from __future__ import annotations
from telegram_utils import send_message

def handle_archive_command(context: dict) -> None:
    """
    Handles the /archive command.
    """
    chat_id = context["chat_id"]
    send_message(chat_id, "The /archive command is not yet implemented.")
