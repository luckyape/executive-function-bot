import os
import json
import logging
import asyncio
from firebase_functions import https_fn, scheduler_fn
import telegram
from agent import Agent
from firestore_client import get_db
from config import get_config, is_safe_mode

# Initialize Logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize Agent
agent = Agent()

def get_telegram_token():
    """
    Retrieves the Telegram token from environment variables.

    Priority:
    1. TELEGRAM_TOKEN environment variable.
    2. CLOUD_RUNTIME_CONFIG environment variable (for backward compatibility).
    3. Fallback to the original get_config from V1.
    """
    # 1. Try the explicit environment variable
    token = os.environ.get('TELEGRAM_TOKEN')
    if token:
        return token

    # 2. Fallback for backward compatibility with `firebase functions:config:set`
    runtime_config_str = os.environ.get('CLOUD_RUNTIME_CONFIG')
    if runtime_config_str:
        try:
            runtime_config = json.loads(runtime_config_str)
            token = runtime_config.get('firebase', {}).get('config', {}).get('telegram', {}).get('token')
            if token:
                return token
        except (json.JSONDecodeError, AttributeError):
            logger.error("Failed to parse CLOUD_RUNTIME_CONFIG")

    # 3. As a final fallback, use the get_config function from config.py for the old V1 logic
    token = get_config("TELEGRAM_TOKEN")
    if token:
        return token

    return None

@https_fn.on_request()
def telegram_webhook(req: https_fn.Request) -> https_fn.Response:
    """
    Firebase Function to handle Telegram webhook requests (Hello Bot).
    """
    # Health check for GET requests or ?ping=1
    if req.method == 'GET' or 'ping' in req.args:
        return https_fn.Response("ok", status=200)

    # Always return 200 to Telegram, even on errors
    try:
        TELEGRAM_TOKEN = get_telegram_token()
        if not TELEGRAM_TOKEN:
            logger.error("Telegram token not set")
            return https_fn.Response("ok", status=200)

        bot = telegram.Bot(token=TELEGRAM_TOKEN)

        update_data = req.get_data(as_text=True)
        update = telegram.Update.de_json(json.loads(update_data), bot)

        chat_id = None
        text = None

        if update.message and update.message.text:
            chat_id = update.message.chat_id
            text = update.message.text
        elif update.edited_message and update.edited_message.text:
            chat_id = update.edited_message.chat_id
            text = update.edited_message.text

        if chat_id and text:
            asyncio.run(bot.send_message(chat_id=chat_id, text="Hello. I am alive."))

    except Exception as e:
        logger.error(f"Unhandled error in webhook: {e}", exc_info=True)

    return https_fn.Response("ok", status=200)


@scheduler_fn.on_schedule(schedule="every day 08:00")
def morning_briefing(event: scheduler_fn.ScheduledEvent) -> None:
    """
    Scheduled Cloud Function for Morning Push.
    """
    logger.info("Starting morning briefing...")

    TELEGRAM_TOKEN = get_telegram_token()
    if not TELEGRAM_TOKEN:
        logger.error("Telegram token not set for morning briefing")
        return

    bot = telegram.Bot(token=TELEGRAM_TOKEN)

    try:
        db = get_db()
        users_ref = db.collection("users")
        docs = users_ref.stream()

        async def send_briefing(user_id, message):
            try:
                await bot.send_message(chat_id=user_id, text=message)
            except Exception as e:
                logger.error(f"Failed to send to {user_id}: {e}")

        count = 0
        for doc in docs:
            user_id = doc.id

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
