from __future__ import annotations

from typing import List, Tuple, Dict, Any

# Single source of truth for command gating
COMMAND_CONFIG: Dict[str, Dict[str, Any]] = {
    # Core commands
    "/start": {"intent": "start", "capabilities": []},
    "/help": {"intent": "help", "capabilities": []},
    "/manual": {"intent": "manual", "capabilities": []},

    # Tasking
    "/list": {"intent": "list_tasks", "capabilities": ["task_read"]},
    "/done": {"intent": "done_task", "capabilities": ["task_write"]},
    "/add": {"intent": "add_task", "capabilities": ["task_write"]},

    # Memory
    "/recall": {"intent": "recall", "capabilities": ["recall"]},
    "/scratch": {"intent": "scratch", "capabilities": ["scratch"]},
    "/archive": {"intent": "archive", "capabilities": ["archive"]},
    "/memory": {"intent": "memory", "capabilities": []},
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
        # NEW: Default to providing task access in plain chat, but not sensitive tools like archive/scratch
        # unless we want "proactive" access. For now, strict 'chat' has no extra capabilities
        # beyond the base tools defined in agent.py (add_task, etc).
        return {"intent": "chat", "capabilities": [], "payload": text}

    parts = stripped.split(maxsplit=1)
    command = parts[0].lower()
    payload = parts[1] if len(parts) > 1 else ""

    config = COMMAND_CONFIG.get(command)
    if config:
        # NEW LOGIC: If the command has a payload, we might want to route it to the Agent 
        # instead of the strict handler, IF the intention is to use the tool with AI assistance.
        #
        # However, to preserve the "innovation" that /command = tool access:
        # We can route ALL known commands to the Agent if we want the Agent to handle the execution,
        # OR we keep the strict handlers for specific ones.
        #
        # The user wants: "/list grocery list..." -> Agent uses list tool + context.
        # But "/list" -> Strict handler.
        #
        # Strategy: 
        # If intent is task/memory related AND there is a payload, route to "chat" 
        # but INJECT the capabilities!
        
        intent = config["intent"]
        capabilities = list(config.get("capabilities", []))

        # List of intents that should degrade to Agent if they have complex arguments
        # (commands that usually take no args or simple args, but user provided natural language)
        agent_handled_intents = {"list_tasks", "recall", "scratch", "archive", "add_task", "done_task"}

        if intent in agent_handled_intents and payload:
             # Route to Agent (intent="chat") but with the command's capabilities unlocked.
             # This effectively "ungates" the tool for this turn.
             return {
                 "intent": "chat",
                 "capabilities": capabilities,
                 "payload": f"User used command {command}. Context/Instruction: {payload}"
             }
        
        return {
            "intent": intent,
            "capabilities": capabilities,
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
