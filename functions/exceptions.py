class HTTPError(Exception):
    """Base exception for HTTP errors."""
    def __init__(self, message="An HTTP error occurred.", status_code=500):
        super().__init__(message)
        self.status_code = status_code

class TelegramWebhookError(HTTPError):
    """Custom exception for Telegram webhook errors."""
    def __init__(self, message="Error processing Telegram webhook.", status_code=200):
        super().__init__(message, status_code)
