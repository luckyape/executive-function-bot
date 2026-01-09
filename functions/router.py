from __future__ import annotations

from typing import List, Tuple, Dict, Any

# Single source of truth for command gating
COMMAND_CONFIG: Dict[str, Dict[str, Any]] = {
    "/recall": {"intent": "recall", "capabilities": ["recall"]},
    "/scratch": {"intent": "scratch", "capabilities": ["scratch"]},
    "/archive": {"intent": "archive", "capabilities": ["archive"]},
    # Add more commands here.
}


def route_update(text: str) -> dict:
    """
    Routes a Telegram text message to the correct intent and capabilities.

    Contract:
      - Non-command text => intent "chat", no capabilities, payload is the full text
      - Known command => intent + capabilities from COMMAND_CONFIG, payload is the remainder
      - Unknown /command => intent "unknown_command", payload is the command token
    """
    if not text:
        return {"intent": "chat", "capabilities": [], "payload": ""}

    stripped = text.strip()

    # Not a command -> plain chat
    if not stripped.startswith("/"):
        return {"intent": "chat", "capabilities": [], "payload": text}

    parts = stripped.split(maxsplit=1)
    command = parts[0].lower()
    payload = parts[1] if len(parts) > 1 else ""

    config = COMMAND_CONFIG.get(command)
    if config:
        return {
            "intent": config["intent"],
            "capabilities": list(config.get("capabilities", [])),
            "payload": payload,
        }

    # Starts with / but not a known command
    return {"intent": "unknown_command", "capabilities": [], "payload": command}


def route_message(message_text: str) -> Tuple[str, List[str], str]:
    """
    Backward-compatible wrapper returning (intent, capabilities, payload).

    This keeps older call sites working while everything moves to route_update().
    """
    route = route_update(message_text or "")
    return route.get("intent", "chat"), route.get("capabilities", []), route.get("payload", "")