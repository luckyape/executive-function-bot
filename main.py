import os
import json
import logging
from firebase_functions import https_fn, scheduler_fn
from firebase_admin import initialize_app, firestore
from telegram import Update, Bot
from agent import Agent
from tools import db # Import db from tools to ensure connection

# Initialize Firebase App
# It might have been initialized in tools.py, but safe to ensure it's up.
try:
    initialize_app()
except ValueError:
    pass

# Initialize Logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize Agent
agent = Agent()

# Initialize Bot (Stateless for function)
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
bot = Bot(token=TELEGRAM_TOKEN) if TELEGRAM_TOKEN else None

@https_fn.on_request()
def telegram_webhook(req: https_fn.Request) -> https_fn.Response:
    """
    HTTP Cloud Function for Telegram Webhook.
    """
    if req.method != "POST":
        return https_fn.Response("Method not allowed", status=405)

    try:
        if not bot:
            logger.error("Telegram token not set")
            return https_fn.Response("Configuration Error", status=500)

        data = req.get_json()
        update = Update.de_json(data, bot)

        if update.message and update.message.text:
            chat_id = update.message.chat_id
            user_id = update.message.from_user.id
            text = update.message.text

            # Process with Agent
            # Using asyncio.run if needed, but python-telegram-bot v20+ is async.
            # However, Cloud Functions 2nd gen handles async if we define the function as async,
            # OR we can just use the synchronous methods if available (PTB is mostly async now).
            # We will use `asyncio.run` inside the sync wrapper or switch to async function definition.
            # firebase_functions supports async def.

            # Let's delegate to a helper logic that handles the async part
            import asyncio
            response_text = agent.generate_response_with_tools(str(user_id), text)

            async def send_reply():
                await bot.send_message(chat_id=chat_id, text=response_text)

            asyncio.run(send_reply())

        return https_fn.Response("OK", status=200)

    except Exception as e:
        logger.error(f"Error processing webhook: {e}")
        return https_fn.Response(f"Error: {str(e)}", status=500)

@scheduler_fn.on_schedule(schedule="every day 08:00")
def morning_briefing(event: scheduler_fn.ScheduledEvent) -> None:
    """
    Scheduled Cloud Function for Morning Push.
    """
    logger.info("Starting morning briefing...")
    if not bot:
        logger.error("Telegram token not set")
        return

    # 1. Fetch all users
    users_ref = db.collection("users")
    docs = users_ref.stream()

    import asyncio

    async def send_briefing(user_id, message):
        try:
            await bot.send_message(chat_id=user_id, text=message)
        except Exception as e:
            logger.error(f"Failed to send to {user_id}: {e}")

    # Process each user
    # Note: For large user bases, this should be fan-out (Pub/Sub), but for this scale, iteration is fine.
    for doc in docs:
        user_id = doc.id
        # We could check timezone here if we stored it and wanted to be precise.
        # For now, we assume global 08:00 UTC trigger as per requirements.

        message = agent.generate_morning_briefing(user_id)
        if message:
            asyncio.run(send_briefing(user_id, message))

    logger.info("Morning briefing complete.")
