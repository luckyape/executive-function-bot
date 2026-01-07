import os
import json
import logging
import asyncio
from firebase_functions import https_fn, scheduler_fn
from telegram import Update, Bot
from agent import Agent
from firestore_client import get_db
from config import get_config, is_safe_mode
from telegram import send_message_safe

# Initialize Logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize Agent
agent = Agent()

# Initialize Bot
TELEGRAM_TOKEN = get_config("TELEGRAM_TOKEN")
bot = Bot(token=TELEGRAM_TOKEN) if TELEGRAM_TOKEN else None

async def handle_safe_mode(user_id: int, chat_id: int, text: str, bot: Bot):
    """
    Deterministic logic for Safe Mode (No LLM).
    Handles core commands directly without NLP/LLM.
    """
    from tools import get_manifesto, set_manifesto, add_task, get_pending_tasks, complete_task

    # 1. Check Manifesto - if not set, any message becomes the manifesto.
    manifesto = get_manifesto(str(user_id))
    if manifesto == "No manifesto set.":
        set_manifesto(str(user_id), text)
        await send_message_safe(bot, chat_id, f"Manifesto set: {text}\n\nI am currently in a simplified mode. I can help you add, list, and complete tasks. Full functionality will be restored shortly.")
        return

    # 2. Command Parsing
    parts = text.strip().lower().split(maxsplit=1)
    command = parts[0] if parts else ""
    args = parts[1] if len(parts) > 1 else ""

    if command in ["add", "/add"]:
        if not args:
            await send_message_safe(bot, chat_id, "[SAFE MODE] Please provide a task description. Usage: add <task>")
            return
        response = add_task(str(user_id), args) # Use original casing for task
        await send_message_safe(bot, chat_id, f"[SAFE MODE] {response}")

    elif command in ["list", "/list"]:
        tasks = get_pending_tasks(str(user_id))
        if not tasks:
            await send_message_safe(bot, chat_id, "[SAFE MODE] No pending tasks.")
        else:
            # Format with index
            msg = "\n".join([f"#{i+1}: {t['description']}" for i, t in enumerate(tasks)])
            await send_message_safe(bot, chat_id, f"[SAFE MODE] Tasks:\n{msg}")

    elif command in ["done", "/done"]:
        response = complete_task(str(user_id), args) # complete_task handles empty args
        await send_message_safe(bot, chat_id, f"[SAFE MODE] {response}")

    else:
        # Fallback for non-commands in safe mode
        await send_message_safe(bot, chat_id, "[SAFE MODE] I can only `add`, `list`, or `done` tasks right now.")

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
