class HTTPError(Exception):
    def __init__(self, status_code: int, message: str):
        self.status_code = status_code
        self.message = message
        super().__init__(f"HTTP {status_code}: {message}")


class NotFoundError(HTTPError):
    def __init__(self, message: str = "Not Found"):
        super().__init__(404, message)


class NotAuthorizedError(HTTPError):
    def __init__(self, message: str = "Not Authorized"):
        super().__init__(403, message)


class BadRequestError(HTTPError):
    def __init__(self, message: str = "Bad Request"):
        super().__init__(400, message)
