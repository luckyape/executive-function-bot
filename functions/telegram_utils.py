import asyncio
import logging
import threading
from telegram import Bot

logger = logging.getLogger(__name__)

_loop = asyncio.new_event_loop()
_loop_lock = threading.Lock()


def _run_in_loop(coro):
    global _loop
    with _loop_lock:
        if _loop.is_closed():
            _loop = asyncio.new_event_loop()
        asyncio.set_event_loop(_loop)
        return _loop.run_until_complete(coro)


def send_message_safe(bot: Bot, chat_id: int, text: str):
    """
    Wrapper to send messages safely, logging errors instead of crashing.
    """
    try:
        _run_in_loop(bot.send_message(chat_id=chat_id, text=text))
    except Exception as e:
        logger.error(f"Failed to send message to {chat_id}: {e}")
