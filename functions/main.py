from telegram_utils import send_message_safe  # IMPORTANT: use local helper, not telegram package

@https_fn.on_request()
def telegram_webhook(req: https_fn.Request) -> https_fn.Response:
    """
    HTTP Cloud Function for Telegram Webhook.
    Always returns 200 OK to Telegram to prevent retry storms.
    """
    data = {}
    update = None

    try:
        # 1) Health check
        if req.method == "GET" or req.args.get("ping"):
            return https_fn.Response("ok", status=200)

        # 2) Telegram sends POST. For anything else: return 200 to avoid noise.
        if req.method != "POST":
            logger.warning("Non-POST request to webhook", extra={"props": {"method": req.method}})
            return https_fn.Response("ok", status=200)

        # 3) Config validation
        if not bot:
            logger.error("Config key 'TELEGRAM_TOKEN' not found in environment variables. Bot not initialized.")
            return https_fn.Response("ok", status=200)

        # 4) Parse update (never raise; never log raw body)
        try:
            data = req.get_json(silent=True) or {}
            update = Update.de_json(data, bot)
        except Exception as e:
            logger.warning(f"Failed to parse Telegram update JSON: {e}", exc_info=True)
            return https_fn.Response("ok", status=200)

        # Ignore non-message updates or non-text messages
        if not update or not getattr(update, "message", None) or not getattr(update.message, "text", None):
            return https_fn.Response("ok", status=200)

        chat_id = update.message.chat_id
        user_id = update.message.from_user.id
        text = update.message.text

        # 5) Basic commands
        if text == "/start":
            asyncio.run(send_message_safe(bot, chat_id, "Welcome! Tell me your Manifesto (Goal)."))
            return https_fn.Response("ok", status=200)

        # 6) Safe mode: deterministic handling only (no LLM calls)
        if is_safe_mode():
            asyncio.run(handle_safe_mode(user_id, chat_id, text, bot))
            return https_fn.Response("ok", status=200)

        # 7) Normal mode: agent
        try:
            response_text = agent.generate_response_with_tools(str(user_id), text)
        except Exception as e:
            logger.error(f"Agent error: {e}", exc_info=True)
            # Do not leak details to user
            asyncio.run(send_message_safe(bot, chat_id, "LLM is unavailable right now. I can still manage tasks."))
            return https_fn.Response("ok", status=200)

        asyncio.run(send_message_safe(bot, chat_id, response_text))
        return https_fn.Response("ok", status=200)

    except TelegramWebhookError as e:
        # Keep as a control-flow/error classification hook; still return 200.
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
            # best-effort notify
            chat_id = (data.get("message", {}).get("chat", {}) or {}).get("id")
            if bot and chat_id:
                asyncio.run(send_message_safe(bot, chat_id, "A critical error occurred."))
        except Exception:
            logger.error("Failed to notify user after unhandled error", exc_info=True)

        return https_fn.Response("ok", status=200)