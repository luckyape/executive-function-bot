import logging
from typing import Dict, Any, Callable

logger = logging.getLogger(__name__)

# A simple command router
COMMAND_MAP: Dict[str, Callable[[Dict[str, Any]], str]] = {}


def command(name: str):
    """
    A decorator to register a command handler.
    """

    def decorator(func: Callable[[Dict[str, Any]], str]):
        COMMAND_MAP[name] = func
        return func

    return decorator


def route_command(text: str, context: Dict[str, Any]) -> str:
    """
    Routes a command to the appropriate handler.
    """
    if not text:
        return "No command provided."

    parts = text.strip().split()
    command_word = parts[0].lower()

    # Strip leading slash to get the command name
    command_name = command_word[1:] if command_word.startswith('/') else command_word

    if command_name in COMMAND_MAP:
        handler = COMMAND_MAP[command_name]
        return handler(context)
    else:
        return f"Unknown command: {command_word}"


from tools import (
    add_to_scratchpad,
    get_scratchpad,
    clear_scratchpad,
    recall_from_archive,
    get_memory_mode,
    set_memory_mode,
    promote_from_scratchpad
)


@command("start")
def start_command(context: Dict[str, Any]) -> str:
    """
    Returns the welcome message.
    """
    return "Welcome! Tell me your Manifesto (Goal)."


@command("memory")
def memory_command(context: Dict[str, Any]) -> str:
    """
    Manages the user's memory mode.
    Usage: /memory [off|hot|hot+projects|strict]
    """
    user_id = context.get("user_id")
    text = context.get("text", "")
    parts = text.strip().split(maxsplit=1)

    if len(parts) < 2:
        current_mode = get_memory_mode(user_id)
        return f"Current memory mode: {current_mode}. To change it, use /memory <mode>."

    new_mode = parts[1].lower()
    return set_memory_mode(user_id, new_mode)


@command("recall")
def recall_command(context: Dict[str, Any]) -> str:
    """
    Searches the user's archive.
    Usage: /recall <query>
    """
    user_id = context.get("user_id")
    text = context.get("text", "")
    parts = text.strip().split(maxsplit=1)

    if len(parts) < 2:
        return "Usage: /recall <query>"

    query = parts[1]
    return recall_from_archive(user_id, query)


@command("scratch")
def scratch_command(context: Dict[str, Any]) -> str:
    """
    Manages the user's scratchpad.
    Usage: /scratch [add <note>|show|clear|promote <index>]
    """
    user_id = context.get("user_id")
    text = context.get("text", "")
    parts = text.strip().split(maxsplit=2)

    if len(parts) < 2:
        return get_scratchpad(user_id)

    subcommand = parts[1].lower()

    if subcommand == "add":
        if len(parts) < 3:
            return "Usage: /scratch add <note>"
        note = parts[2]
        return add_to_scratchpad(user_id, note)
    elif subcommand == "show":
        return get_scratchpad(user_id)
    elif subcommand == "clear":
        return clear_scratchpad(user_id)
    elif subcommand == "promote":
        if len(parts) < 3:
            return "Usage: /scratch promote <number>"
        try:
            # The tool now expects a 1-based index
            index = int(parts[2])
            return promote_from_scratchpad(user_id, index)
        except ValueError:
            return "Invalid note number. Please provide a number."
    else:
        return "Unknown subcommand for /scratch. Use 'add', 'show', 'clear', or 'promote'."


@command("help")
def help_command(context: Dict[str, Any]) -> str:
    """
    Returns a list of available commands.
    """
    return "Available commands: /start, /help, /scratch, /recall, /memory"
