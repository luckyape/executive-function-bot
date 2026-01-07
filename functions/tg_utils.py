import logging
import os
from typing import Any, Dict

import requests

logger = logging.getLogger(__name__)


def _build_send_message_payload(chat_id: int, text: str) -> Dict[str, Any]:
    return {
        "chat_id": chat_id,
        "text": text,
        "disable_web_page_preview": True,
    }


def send_message_safe(chat_id: int, text: str) -> bool:
    """
    Send a Telegram message via the HTTP API, logging errors instead of crashing.
    """
    token = os.getenv("TELEGRAM_TOKEN")
    if not token:
        logger.error("TELEGRAM_TOKEN is missing; cannot send Telegram message.")
        return False

    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = _build_send_message_payload(chat_id, text)

    try:
        response = requests.post(url, json=payload, timeout=10)
    except requests.RequestException as exc:
        logger.error("Telegram sendMessage request failed: %s", exc)
        return False

    if not response.ok:
        logger.error(
            "Telegram sendMessage failed (%s): %s",
            response.status_code,
            response.text,
        )
        return False

    return True
