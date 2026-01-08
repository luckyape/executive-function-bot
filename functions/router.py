COMMAND_CONFIG = {
    "/recall": {"intent": "recall", "capabilities": ["recall"]},
    "/scratch": {"intent": "scratch", "capabilities": ["scratch"]},
    "/archive": {"intent": "archive", "capabilities": ["archive"]},
}

def route_update(text: str) -> dict:
    """
    Routes a Telegram update to the correct intent and capabilities.
    """
    if not text:
        return {"intent": "chat", "capabilities": [], "payload": ""}

    stripped_text = text.strip()
    if not stripped_text.startswith("/"):
        return {"intent": "chat", "capabilities": [], "payload": text}

    parts = stripped_text.split(maxsplit=1)
    command = parts[0].lower()
    payload = parts[1] if len(parts) > 1 else ""

    if command in COMMAND_CONFIG:
        config = COMMAND_CONFIG[command]
        return {
            "intent": config["intent"],
            "capabilities": config["capabilities"],
            "payload": payload,
        }

    # Starts with / but not a known command
    return {"intent": "unknown_command", "capabilities": [], "payload": command}
