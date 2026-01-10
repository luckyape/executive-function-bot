from __future__ import annotations
from telegram_utils import send_message

def handle_archive_command(context: dict) -> None:
    """
    Handles the /archive command.
    """
    send_message(context["chat_id"], "To search your archive, use: /archive <query>\nExample: /archive taxes")
