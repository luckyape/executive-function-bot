import logging
from telegram import Bot

logger = logging.getLogger(__name__)

async def send_message_safe(bot: Bot, chat_id: int, text: str):
    """
    Wrapper to send messages safely, logging errors instead of crashing.
    """
    try:
        await bot.send_message(chat_id=chat_id, text=text)
    except Exception as e:
        logger.error(f"Failed to send message to {chat_id}: {e}")
