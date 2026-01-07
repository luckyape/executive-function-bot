import json
import logging
import asyncio

from firebase_functions import https_fn, scheduler_fn
from telegram import Update, Bot

from agent import Agent
from firestore_client import get_db
from config import get_config, is_safe_mode
from telegram_utils import send_message_safe  # IMPORTANT: local helper, not telegram package
from exceptions import TelegramWebhookError

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

agent = Agent()

TELEGRAM_TOKEN = get_config("TELEGRAM_TOKEN")
bot = Bot(token=TELEGRAM_TOKEN) if TELEGRAM_TOKEN else None


async def handle_safe_mode(user_id: int, chat_id: int, text: str, bot: Bot, from_fallback: bool = False):
    """
    Deterministic logic for Safe Mode (No LLM).
    """
    from tools import get_manifesto, set_manifesto, add_task, get_pending_tasks, complete_task

    if from_fallback:
        await send_message_safe(
            bot,
            chat_id,
            "LLM is rate-limited, so I’m in Safe Mode. You can still: add <task>, list, done <fragment>."
        )

    text_lower = text.lower().strip()

    # 1) Manifesto initialization
    manifesto = get_manifesto(str(user_id))
    if manifesto == "No manifesto set.":
        set_manifesto(str(user_id), text)
        await send_message_safe(bot, chat_id, f"[SAFE MODE] Manifesto set: {text}")
        return

    # 2) Commands
    if text_lower.startswith("add "):
        task = text[4:].strip()
        add_task(str(user_id), task)
        await send_message_safe(bot, chat_id, f"[SAFE MODE] Task added: {task}")
        return

    if text_lower in ("list", "/list"):
        tasks = get_pending_tasks(str(user_id))
        if not tasks:
            await send_message_safe(bot, chat_id, "[SAFE MODE] No pending tasks.")
            return

        lines = []
        for t in tasks:
            idx = t.get("index")
            desc = t.get("description", "")
            if idx is not None:
                lines.append(f"#{idx} - {desc}")
            else:
                lines.append(f"- {desc}")

        await send_message_safe(bot, chat_id, "[SAFE MODE] Tasks:\n" + "\n".join(lines))
        return

    if text_lower.startswith("done"):
        # supports: "done", "done #1", "done pay rent"
        query = text[4:].strip()
        res = complete_task(str(user_id), query)
        await send_message_safe(bot, chat_id, f"[SAFE MODE] {res}")
        return

    await send_message_safe(bot, chat_id, "[SAFE MODE] Unknown command. Try: add <task>, list, done <fragment>.")


@https_fn.on_request()
def telegram_webhook(req: https_fn.Request) -> https_fn.Response:
    """
    Telegram webhook. Always return 200 to prevent retry storms.
    """
    data = {}
    update = None

    try:
        # Health check
        if req.method == "GET" or req.args.get("ping"):
            return https_fn.Response("ok", status=200)

        if req.method != "POST":
            logger.warning("Non-POST request to webhook", extra={"props": {"method": req.method}})
            return https_fn.Response("ok", status=200)

        if not bot:
            logger.error("Config key 'TELEGRAM_TOKEN' not found in environment variables. Bot not initialized.")
            return https_fn.Response("ok", status=200)

        # Parse update (never raise; never log raw body)
        try:
            data = req.get_json(silent=True) or {}
            update = Update.de_json(data, bot)
        except Exception as e:
            logger.warning(f"Failed to parse Telegram update JSON: {e}", exc_info=True)
            return https_fn.Response("ok", status=200)

        if not update or not getattr(update, "message", None) or not getattr(update.message, "text", None):
            return https_fn.Response("ok", status=200)

        chat_id = update.message.chat_id
        user_id = update.message.from_user.id
        text = update.message.text

        if text == "/start":
            asyncio.run(send_message_safe(bot, chat_id, "Welcome! Tell me your Manifesto (Goal)."))
            return https_fn.Response("ok", status=200)

        # Explicit safe mode (env toggle)
        if is_safe_mode():
            asyncio.run(handle_safe_mode(user_id, chat_id, text, bot))
            return https_fn.Response("ok", status=200)

        # Normal mode: agent
        try:
            response_text = agent.generate_response_with_tools(str(user_id), text)
        except Exception as e:
            logger.error(f"Agent error: {e}", exc_info=True)
            asyncio.run(send_message_safe(bot, chat_id, "LLM is unavailable right now. I can still manage tasks."))
            asyncio.run(handle_safe_mode(user_id, chat_id, text, bot, from_fallback=True))
            return https_fn.Response("ok", status=200)

        # Rate-limit fallback: if agent returns the known rate-limit string, switch to safe mode for this request
        if isinstance(response_text, str) and response_text.startswith("LLM is rate-limited"):
            asyncio.run(handle_safe_mode(user_id, chat_id, text, bot, from_fallback=True))
            return https_fn.Response("ok", status=200)

        asyncio.run(send_message_safe(bot, chat_id, response_text))
        return https_fn.Response("ok", status=200)

    except TelegramWebhookError as e:
        logger.error(f"Caught TelegramWebhookError: {e}", exc_info=True)
        try:
            chat_id = (data.get("message", {}).get("chat", {}) or {}).get("id")
            if bot and chat_id:
                asyncio.run(send_message_safe(bot, chat_id, "I hit an internal error, but I'm still alive. Try again."))
        except Exception:
            logger.error("Failed to notify user after TelegramWebhookError", exc_info=True)
        return https_fn.Response("ok", status=200)

    except Exception as e:
        logger.error(f"Unhandled error in webhook: {e}", exc_info=True)
        try:
            chat_id = (data.get("message", {}).get("chat", {}) or {}).get("id")
            if bot and chat_id:
                asyncio.run(send_message_safe(bot, chat_id, "A critical error occurred."))
        except Exception:
            logger.error("Failed to notify user after unhandled error", exc_info=True)
        return https_fn.Response("ok", status=200)