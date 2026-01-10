def handle_recall_command(context: dict) -> None:
    """
    Handles the /recall command.
    """
    from telegram_utils import send_message
    
    send_message(context["chat_id"], "To recall memories, use: /recall <query>\nExample: /recall project alpha")

def handle_archive_command(context: dict) -> None:
    """
    Handles the /archive command.
    """
    from telegram_utils import send_message
    
    send_message(context["chat_id"], "To search your archive, use: /archive <query>\nExample: /archive taxes")
