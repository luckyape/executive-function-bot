import logging
import asyncio

from firebase_functions import https_fn, scheduler_fn
from telegram import Update, Bot

from agent import Agent
from firestore_client import get_db
from config import get_config, is_safe_mode
from telegram_utils import send_message_safe  # local helper (NOT the telegram package)
from commands.help import get_help_text

# Logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Agent
agent = Agent()

# Config (token may arrive via env/secrets)
TELEGRAM_TOKEN = get_config("TELEGRAM_TOKEN")


def _send(chat_id: int, text: str) -> None:
    """
    Send a Telegram message safely.
    Works whether send_message_safe is sync or async.
    Avoids keeping a global Bot tied to a closed event loop.
    """
    if not TELEGRAM_TOKEN:
        logger.error("Config key 'TELEGRAM_TOKEN' not found in environment variables.")
        return

    bot = Bot(token=TELEGRAM_TOKEN)
    try:
        result = send_message_safe(bot, chat_id, text)
        if asyncio.iscoroutine(result):
            asyncio.run(result)
    except RuntimeError as e:
        logger.error(f"Failed to send message (RuntimeError): {e}", exc_info=True)
    except Exception as e:
        logger.error(f"Failed to send message: {e}", exc_info=True)


def handle_safe_mode(user_id: int, chat_id: int, text: str, from_fallback: bool = False) -> None:
    """
    Deterministic logic for Safe Mode (no LLM calls).
    """
    from tools import get_manifesto, set_manifesto, add_task, get_pending_tasks, complete_task

    if from_fallback:
        _send(chat_id, "LLM is busy right now, so I'm in Safe Mode. You can still: add <task>, list, done <fragment>.")

    text_lower = (text or "").lower().strip()

    # 1) Manifesto bootstrap
    manifesto = get_manifesto(str(user_id))
    if manifesto == "No manifesto set.":
        set_manifesto(str(user_id), text)
        _send(chat_id, f"[SAFE MODE] Manifesto set: {text}")
        return

    # 2) Commands
    if text_lower.startswith("add "):
        task = text[4:].strip()
        add_task(str(user_id), task)
        _send(chat_id, f"[SAFE MODE] Task added: {task}")
        return

    if text_lower in ("list", "/list"):
        tasks = get_pending_tasks(str(user_id))
        if not tasks:
            _send(chat_id, "[SAFE MODE] No pending tasks.")
            return

        lines = []
        for t in tasks:
            idx = t.get("index")
            desc = t.get("description", "")
            if idx is not None:
                lines.append(f"#{idx} - {desc}")
            else:
                lines.append(f"- {desc}")

        _send(chat_id, "[SAFE MODE] Tasks:\n" + "\n".join(lines))
        return

    if text_lower.startswith("done"):
        query = text[4:].strip()
        res = complete_task(str(user_id), query)
        _send(chat_id, f"[SAFE MODE] {res}")
        return

    _send(chat_id, "[SAFE MODE] Unknown command. Try: add <task>, list, done <fragment>.")


@https_fn.on_request()
def telegram_webhook(req: https_fn.Request) -> https_fn.Response:
    """
    HTTP Cloud Function for Telegram Webhook.
    MUST always return 200 OK to Telegram to prevent retry storms.
    """
    data = {}
    try:
        # 1) Health check
        if req.method == "GET" or req.args.get("ping"):
            return https_fn.Response("ok", status=200)

        # 2) Telegram sends POST; for anything else, quietly 200.
        if req.method != "POST":
            logger.warning(f"Non-POST request to webhook: {req.method}")
            return https_fn.Response("ok", status=200)

        # 3) Config validation
        if not TELEGRAM_TOKEN:
            logger.error("Config key 'TELEGRAM_TOKEN' not found in environment variables.")
            return https_fn.Response("ok", status=200)

        # 4) Parse update (never raise; never log raw body)
        try:
            data = req.get_json(silent=True) or {}
            bot_for_parse = Bot(token=TELEGRAM_TOKEN)
            update = Update.de_json(data, bot_for_parse)
        except Exception as e:
            logger.warning(f"Failed to parse Telegram update JSON: {e}", exc_info=True)
            return https_fn.Response("ok", status=200)

        # Ignore non-message updates or non-text messages
        if not update or not getattr(update, "message", None) or not getattr(update.message, "text", None):
            return https_fn.Response("ok", status=200)

        chat_id = update.message.chat_id
        user_id = update.message.from_user.id
        text = update.message.text

        # 5) /start, /scratch
        if text == "/start":
            _send(chat_id, "Welcome! Tell me your Manifesto (Goal).")
            return https_fn.Response("ok", status=200)

        if text.startswith("/scratch"):
            from commands.scratch import handle_scratch_command
            handle_scratch_command(update.message.to_dict())
        # Handle /help
        if text == "/help":
            _send(chat_id, get_help_text())
            return https_fn.Response("ok", status=200)

        # Handle /memory (supports "/memory ..." subcommands)
        if text.startswith("/memory"):
            from commands.memory import handle_memory_command
            response_text = handle_memory_command(str(user_id), text)
            _send(chat_id, response_text)
            return https_fn.Response("ok", status=200)
            return https_fn.Response("ok", status=200)

        # 6) Safe mode forced
        if is_safe_mode():
            handle_safe_mode(user_id, chat_id, text)
            return https_fn.Response("ok", status=200)

        # 7) Normal mode: agent
        try:
            response_text = agent.generate_response_with_tools(str(user_id), text)
        except Exception as e:
            logger.error(f"Agent error: {e}", exc_info=True)
            handle_safe_mode(user_id, chat_id, text, from_fallback=True)
            return https_fn.Response("ok", status=200)

        # 8) Rate-limit fallback (string contract)
        if isinstance(response_text, str) and response_text.startswith("LLM is rate-limited"):
            handle_safe_mode(user_id, chat_id, text, from_fallback=True)
            return https_fn.Response("ok", status=200)

        _send(chat_id, response_text)
        return https_fn.Response("ok", status=200)

    except Exception as e:
        logger.error(f"Unhandled error in webhook: {e}", exc_info=True)
        try:
            chat_id = (data.get("message", {}).get("chat", {}) or {}).get("id")
            if chat_id:
                _send(chat_id, "A critical error occurred.")
        except Exception:
            logger.error("Failed to notify user after unhandled error", exc_info=True)

        return https_fn.Response("ok", status=200)


@scheduler_fn.on_schedule(schedule="every day 08:00")
def morning_briefing(event: scheduler_fn.ScheduledEvent) -> None:
    """
    Scheduled Cloud Function for Morning Push.
    """
    logger.info("Starting morning briefing...")

    if not TELEGRAM_TOKEN:
        logger.error("Config key 'TELEGRAM_TOKEN' not found in environment variables.")
        return

    try:
        db = get_db()
        users_ref = db.collection("users")
        docs = users_ref.stream()

        count = 0
        for doc in docs:
            user_id = doc.id

            if is_safe_mode():
                continue

            try:
                message = agent.generate_morning_briefing(user_id)
                if message:
                    _send(int(user_id), message)
                    count += 1
            except Exception as e:
                logger.error(f"Error generating briefing for {user_id}: {e}", exc_info=True)

        logger.info(f"Morning briefing complete. Sent to {count} users.")

    except Exception as e:
        logger.error(f"Morning briefing failed: {e}", exc_info=True)
