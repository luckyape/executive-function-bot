class HTTPError(Exception):
    """Base exception for HTTP errors."""
    def __init__(self, status_code: int, message: str):
        self.status_code = status_code
        self.message = message
        super().__init__(f"HTTP {status_code}: {message}")


class BadRequestError(HTTPError):
    def __init__(self, message: str = "Bad Request"):
        super().__init__(400, message)


class NotAuthorizedError(HTTPError):
    def __init__(self, message: str = "Not Authorized"):
        super().__init__(403, message)


class NotFoundError(HTTPError):
    def __init__(self, message: str = "Not Found"):
        super().__init__(404, message)


class TelegramWebhookError(HTTPError):
    """
    Used for *control flow* in the Telegram webhook handler.
    IMPORTANT: The handler should still return HTTP 200 to Telegram to avoid retries.
    Do not treat this as an actual non-200 HTTP response unless you know what you're doing.
    """
    def __init__(self, message: str = "Error processing Telegram webhook."):
        # Keep this as a semantic error type; response code is decided by the handler.
        super().__init__(200, message)
