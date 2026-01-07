import os
import json
import logging
from firebase_functions import https_fn
import telegram

# Initialize Logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def get_telegram_token():
    """
    Retrieves the Telegram token from environment variables.

    Priority:
    1. TELEGRAM_TOKEN environment variable.
    2. CLOUD_RUNTIME_CONFIG environment variable (for backward compatibility).
    """
    token = os.environ.get('TELEGRAM_TOKEN')
    if token:
        return token

    # Backward compatibility for firebase functions:config:set
    runtime_config = os.environ.get('CLOUD_RUNTIME_CONFIG')
    if runtime_config:
        try:
            config = json.loads(runtime_config)
            token = config.get('firebase', {}).get('config', {}).get('telegram', {}).get('token')
            if token:
                return token
        except json.JSONDecodeError:
            logger.error("Failed to parse CLOUD_RUNTIME_CONFIG")

    return None

@https_fn.on_request()
def telegram_webhook(req: https_fn.Request) -> https_fn.Response:
    """
    Firebase Function to handle Telegram webhook requests.
    """
    # Health check for GET requests or ?ping=1
    if req.method == 'GET' or 'ping' in req.args:
        return https_fn.Response("ok", status=200)

    try:
        TELEGRAM_TOKEN = get_telegram_token()
        if not TELEGRAM_TOKEN:
            logger.error("Telegram token not set")
            return https_fn.Response("ok", status=200)

        bot = telegram.Bot(token=TELEGRAM_TOKEN)

        # We need to use `get_data` as `get_json` has issues in some environments
        update_data = req.get_data(as_text=True)
        update = telegram.Update.de_json(json.loads(update_data), bot)

        chat_id = None
        text = None

        if update.message:
            chat_id = update.message.chat_id
            text = update.message.text
        elif update.edited_message:
            chat_id = update.edited_message.chat_id
            text = update.edited_message.text

        if chat_id and text:
            bot.send_message(chat_id=chat_id, text="Hello. I am alive.")

        return https_fn.Response("ok", status=200)

    except Exception as e:
        # Catch all exceptions to ensure a 200 response to Telegram
        logger.error(f"Unhandled error in webhook: {e}", exc_info=True)
        return https_fn.Response("ok", status=200)
