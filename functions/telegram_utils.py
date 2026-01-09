import logging
import asyncio
from telegram import Bot
from config import get_config

logger = logging.getLogger(__name__)

async def send_message_safe(bot: Bot, chat_id: int, text: str):
    """
    Wrapper to send messages safely, logging errors instead of crashing.
    """
    try:
        await bot.send_message(chat_id=chat_id, text=text)
    except Exception as e:
        logger.error(f"Failed to send message to {chat_id}: {e}")


def split_message(text: str, chunk_size: int = 4096) -> list[str]:
    """
    Splits a long string into a list of smaller strings, each within a given size limit.
    """
    if not text:
        return []

    chunks = []
    for i in range(0, len(text), chunk_size):
        chunks.append(text[i:i + chunk_size])
    return chunks
