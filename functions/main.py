import os
import json
import logging
import asyncio
from firebase_functions import https_fn, scheduler_fn
from telegram import Update, Bot
from agent import Agent
from firestore_client import get_db
from config import get_config, is_safe_mode

# Initialize Logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize Agent
agent = Agent()

# Initialize Bot (Lazy load or global if safe)
# We use get_config to be robust
TELEGRAM_TOKEN = get_config("TELEGRAM_TOKEN")
bot = Bot(token=TELEGRAM_TOKEN) if TELEGRAM_TOKEN else None

@https_fn.on_request()
def telegram_webhook(req: https_fn.Request) -> https_fn.Response:
    """
    HTTP Cloud Function for Telegram Webhook.
    """
    # 1. Health Check & Method validation
    if req.method == "GET" or req.args.get("ping"):
        return https_fn.Response("ok", status=200)

    if req.method != "POST":
        return https_fn.Response("Method not allowed", status=405)

    try:
        # 2. Config Validation
        if not bot:
            logger.error("Telegram token not set")
            # Return 200 to prevent Telegram retry loop on config error
            return https_fn.Response("Configuration Error: Token missing", status=200)

        # 3. Parse Update
        try:
            data = req.get_json()
            update = Update.de_json(data, bot)
        except Exception as e:
            logger.error(f"Failed to parse update: {e}")
            return https_fn.Response("Parse Error", status=200)

        if not update:
            return https_fn.Response("OK (No update)", status=200)

        # 4. Handle Message
        if update.message and update.message.text:
            chat_id = update.message.chat_id
            user_id = update.message.from_user.id
            text = update.message.text

            # Check Safe Mode
            if is_safe_mode():
                logger.info(f"SAFE MODE: Echoing '{text}'")
                asyncio.run(bot.send_message(chat_id=chat_id, text=f"[SAFE MODE] Echo: {text}"))
                return https_fn.Response("OK (Safe Mode)", status=200)

            # Process with Agent
            try:
                response_text = agent.generate_response_with_tools(str(user_id), text)
                asyncio.run(bot.send_message(chat_id=chat_id, text=response_text))
            except Exception as e:
                logger.error(f"Agent/Telegram Error: {e}")
                # Try to send error to user if possible, or just log
                try:
                    asyncio.run(bot.send_message(chat_id=chat_id, text="I encountered an internal error. Please try again later."))
                except:
                    pass

        # Handle other updates (non-text, edited, etc)
        elif update.edited_message:
            # Ignore or handle edits
            pass

        return https_fn.Response("OK", status=200)

    except Exception as e:
        # Catch-all to prevent 500
        logger.error(f"Unhandled error in webhook: {e}")
        return https_fn.Response("Internal Server Error (Logged)", status=200)

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

        async def send_briefing(user_id, message):
            try:
                await bot.send_message(chat_id=user_id, text=message)
            except Exception as e:
                logger.error(f"Failed to send to {user_id}: {e}")

        # Process each user
        count = 0
        for doc in docs:
            user_id = doc.id

            # Skip if safe mode
            if is_safe_mode():
                logger.info(f"SAFE MODE: Skipping briefing for {user_id}")
                continue

            try:
                message = agent.generate_morning_briefing(user_id)
                if message:
                    asyncio.run(send_briefing(user_id, message))
                    count += 1
            except Exception as e:
                logger.error(f"Error generating briefing for {user_id}: {e}")

        logger.info(f"Morning briefing complete. Sent to {count} users.")

    except Exception as e:
        logger.error(f"Morning briefing failed: {e}")
