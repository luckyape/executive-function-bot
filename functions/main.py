import os
import json
import logging
import asyncio
from firebase_functions import https_fn, scheduler_fn
from telegram import Update, Bot
from agent import Agent, GeminiRateLimitError
from firestore_client import get_db
from config import get_config, is_safe_mode
from telegram_utils import send_message_safe

# Initialize Logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize Agent
agent = Agent()

# Initialize Bot
TELEGRAM_TOKEN = get_config("TELEGRAM_TOKEN")
bot = Bot(token=TELEGRAM_TOKEN) if TELEGRAM_TOKEN else None

async def handle_safe_mode(user_id: int, chat_id: int, text: str, bot: Bot, from_fallback: bool = False):
    """
    Deterministic logic for Safe Mode (No LLM).
    """
    from tools import get_manifesto, set_manifesto, add_task, get_pending_tasks, complete_task

    if from_fallback:
        await send_message_safe(bot, chat_id, "My AI brain is a bit busy right now, so I'm in Safe Mode. You can still 'add', 'list', or 'done' tasks.")

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
            msg = "\n".join([f"- {t['description']}" for t in tasks])
            await send_message_safe(bot, chat_id, f"[SAFE MODE] Tasks:\n{msg}")
    elif text_lower.startswith("done "):
        frag = text[5:].strip()
        res = complete_task(str(user_id), frag)
        await send_message_safe(bot, chat_id, f"[SAFE MODE] {res}")
    else:
        await send_message_safe(bot, chat_id, f"[SAFE MODE] Unknown command. Available: add <task>, list, done <fragment>.")

@https_fn.on_request()
def telegram_webhook(req: https_fn.Request) -> https_fn.Response:
    """
    HTTP Cloud Function for Telegram Webhook.
    """
    # Global Try/Except to prevent 500s
    try:
        # 1. Health Check
        if req.method == "GET" or req.args.get("ping"):
            return https_fn.Response("ok", status=200)

        if req.method != "POST":
            return https_fn.Response("Method not allowed", status=405)

        # 2. Config Validation
        if not bot:
            logger.error("Telegram token not set")
            return https_fn.Response("Configuration Error", status=200)

        # 3. Parse Update
        try:
            data = req.get_json()
            update = Update.de_json(data, bot)
        except Exception as e:
            logger.error(f"Failed to parse update: {e}")
            return https_fn.Response("ok", status=200)

        if not update:
            return https_fn.Response("ok", status=200)

        # 4. Handle Message
        # Handle text messages
        if update.message:
             # Handle new user /start
            if update.message.text == "/start":
                 asyncio.run(send_message_safe(bot, update.message.chat_id, "Welcome! Tell me your Manifesto (Goal)."))
                 return https_fn.Response("ok", status=200)

            if update.message.text:
                chat_id = update.message.chat_id
                user_id = update.message.from_user.id
                text = update.message.text

                # Check Safe Mode
                if is_safe_mode():
                    asyncio.run(handle_safe_mode(user_id, chat_id, text, bot))
                    return https_fn.Response("ok", status=200)

                # Process with Agent
                try:
                    # TODO: Implement timeout logic if needed, but Cloud Functions has its own timeout.
                    response_text = agent.generate_response_with_tools(str(user_id), text)
                    asyncio.run(send_message_safe(bot, chat_id, response_text))
                except GeminiRateLimitError:
                    # Fallback to Safe Mode on 429
                    logger.warning(f"Gemini rate limited. Switching to safe mode for user {user_id}")
                    asyncio.run(handle_safe_mode(user_id, chat_id, text, bot, from_fallback=True))
                except Exception as e:
                    logger.error(f"Agent Error: {e}")
                    asyncio.run(send_message_safe(bot, chat_id, "I encountered an internal error."))

            # Handle Captions (for photos/docs with text)
            elif update.message.caption:
                 # Treat caption as text?
                 pass

        # Handle Edited Messages
        elif update.edited_message:
            # Optionally handle
            pass

        return https_fn.Response("ok", status=200)

    except Exception as e:
        logger.exception(f"Unhandled error in webhook: {e}")
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
