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


def send_message(chat_id: int, text: str) -> None:
    """
    Send a Telegram message synchronously.
    This is a convenience wrapper for command handlers.
    Works whether send_message_safe is sync or async.
    """
    token = get_config("TELEGRAM_TOKEN")
    if not token:
        logger.error("Config key 'TELEGRAM_TOKEN' not found in environment variables.")
        return

    bot = Bot(token=token)
    try:
        result = send_message_safe(bot, chat_id, text)
        if asyncio.iscoroutine(result):
            asyncio.run(result)
    except RuntimeError as e:
        logger.error(f"Failed to send message (RuntimeError): {e}", exc_info=True)
    except Exception as e:
        logger.error(f"Failed to send message: {e}", exc_info=True)


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
