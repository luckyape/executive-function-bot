from typing import Dict, Any, List, Tuple

COMMAND_CONFIG = {
    "/recall": {
        "intent": "recall",
        "capabilities": ["recall"],
    },
    # Future commands can be added here
}

def route_message(message_text: str) -> Tuple[str, List[str], str]:
    """
    Parses a message to determine intent and grant capabilities.
    """
    if not message_text:
        return "chat", [], ""

    # Check for a command
    first_word = message_text.split(" ", 1)[0]
    config = COMMAND_CONFIG.get(first_word)

    if config:
        intent = config["intent"]
        capabilities = config["capabilities"]
        payload = message_text.removeprefix(first_word).strip()
        return intent, capabilities, payload

    # Default to chat
    return "chat", [], message_text
