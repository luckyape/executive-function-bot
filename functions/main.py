import os
import json
import logging
import asyncio
import json_logging
from firebase_functions import https_fn, scheduler_fn
from telegram import Update, Bot
from agent import Agent
from firestore_client import get_db
from config import get_config, is_safe_mode
from telegram import send_message_safe
from exceptions import TelegramWebhookError

# Initialize Logger
json_logging.init_non_web(enable_json=True)
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
logger.addHandler(logging.StreamHandler())

# Initialize Agent
agent = Agent()

# Initialize Bot
TELEGRAM_TOKEN = get_config("TELEGRAM_TOKEN")
bot = Bot(token=TELEGRAM_TOKEN) if TELEGRAM_TOKEN else None

async def handle_safe_mode(user_id: int, chat_id: int, text: str, bot: Bot):
    """
    Deterministic logic for Safe Mode (No LLM).
    """
    from tools import get_manifesto, set_manifesto, add_task, get_pending_tasks, complete_task

    text_lower = text.lower().strip()

    # 1. Check Manifesto
    manifesto = get_manifesto(str(user_id))
    if manifesto == "No manifesto set.":
        set_manifesto(str(user_id), text)
        await send_message_safe(bot, chat_id, f"[SAFE MODE] Manifesto set: {text}")
        return

    # 2. Commands
    if text_lower.startswith("add "):
        task = text[4:].strip()
        add_task(str(user_id), task)
        await send_message_safe(bot, chat_id, f"[SAFE MODE] Task added: {task}")
    elif text_lower == "list" or text_lower == "/list":
        tasks = get_pending_tasks(str(user_id))
        if not tasks:
            await send_message_safe(bot, chat_id, "[SAFE MODE] No pending tasks.")
        else:
            # Format with index
            msg = "\n".join([f"#{t['index']} - {t['description']}" for t in tasks])
            await send_message_safe(bot, chat_id, f"[SAFE MODE] Tasks:\n{msg}")
    elif text_lower.startswith("done"):
        # Pass the whole fragment, e.g., "done #1" -> "#1"
        # "done" -> ""
        # "done task" -> "task"
        query = text[4:].strip()
        res = complete_task(str(user_id), query)
        await send_message_safe(bot, chat_id, f"[SAFE MODE] {res}")
    else:
        await send_message_safe(bot, chat_id, f"[SAFE MODE] Unknown command. Available: add <task>, list, done <fragment>.")

@https_fn.on_request()
def telegram_webhook(req: https_fn.Request) -> https_fn.Response:
    """
    HTTP Cloud Function for Telegram Webhook.
    """
    data = {}
    try:
        # 1. Health Check
        if req.method == "GET" or req.args.get("ping"):
            return https_fn.Response("ok", status=200)

        if req.method != "POST":
            raise TelegramWebhookError("Invalid request method", status_code=405)

        # 2. Config Validation
        if not bot:
            logger.error("TELEGRAM_TOKEN is not set.")
            # Still return 200 to Telegram, but log the error.
            raise TelegramWebhookError("Application not configured.")

        # 3. Parse Update
        try:
            data = req.get_json()
            update = Update.de_json(data, bot)
        except json.JSONDecodeError as e:
            logger.error(f"JSON Decode Error: {e}")
            raise TelegramWebhookError("Invalid JSON received.")

        if not update or not update.message:
            return https_fn.Response("ok", status=200)

        # From here, we can rely on the TelegramWebhookError handler.
        if not update.message.text:
             return https_fn.Response("ok", status=200)

        chat_id = update.message.chat_id
        user_id = update.message.from_user.id
        text = update.message.text

        # 4. Handle different message types
        if text == "/start":
            asyncio.run(send_message_safe(bot, chat_id, "Welcome! Tell me your Manifesto (Goal)."))
            return https_fn.Response("ok", status=200)

        if is_safe_mode():
            asyncio.run(handle_safe_mode(user_id, chat_id, text, bot))
        else:
            try:
                response_text = agent.generate_response_with_tools(str(user_id), text)
                asyncio.run(send_message_safe(bot, chat_id, response_text))
            except Exception as e:
                logger.error(f"Agent Error: {e}", exc_info=True)
                raise TelegramWebhookError("Agent failed to generate response.")

        return https_fn.Response("ok", status=200)

    except TelegramWebhookError as e:
        # Log the detailed error but send a generic message to the user.
        logger.error(f"Caught Telegram Webhook Error: {e}", exc_info=True)
        # Attempt to get chat_id from the request to notify the user.
        try:
            chat_id = data.get("message", {}).get("chat", {}).get("id")
            if bot and chat_id:
                asyncio.run(send_message_safe(bot, chat_id, "I encountered an internal error."))
        except Exception as notify_e:
            logger.error(f"Could not notify user of error: {notify_e}")

        # Always return a 200 to Telegram to prevent re-sends.
        return https_fn.Response("ok", status=200)

    except Exception as e:
        logger.error(f"Unhandled Exception: {e}", exc_info=True)
        # Attempt to notify user as a last resort
        try:
            chat_id = data.get("message", {}).get("chat", {}).get("id")
            if bot and chat_id:
                asyncio.run(send_message_safe(bot, chat_id, "A critical error occurred."))
        except Exception as notify_e:
            logger.error(f"Could not notify user of critical error: {notify_e}")

        return https_fn.Response("ok", status=200)

@scheduler_fn.on_schedule(schedule="every day 08:00")
def morning_briefing(event: scheduler_fn.ScheduledEvent) -> None:
    """
    Scheduled Cloud Function for Morning Push.
    """
    logger.info("Starting morning briefing...")
    if not bot:
        logger.error("Telegram token not set")
        return

    try:
        # 1. Fetch all users
        db = get_db()
        users_ref = db.collection("users")
        docs = users_ref.stream()

        # Process each user
        count = 0
        for doc in docs:
            user_id = doc.id

            if is_safe_mode():
                continue

            try:
                message = agent.generate_morning_briefing(user_id)
                if message:
                    asyncio.run(send_message_safe(bot, int(user_id), message))
                    count += 1
            except Exception as e:
                logger.error(f"Error generating briefing for {user_id}: {e}")

        logger.info(f"Morning briefing complete. Sent to {count} users.")

    except Exception as e:
        logger.error(f"Morning briefing failed: {e}")
