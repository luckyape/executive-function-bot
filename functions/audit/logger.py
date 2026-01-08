import logging
from typing import Any, Dict, Optional

from ..db.audit_repo import save_audit_log

logger = logging.getLogger(__name__)


def _log(user_id: str, event_type: str, event_data: Dict[str, Any]) -> None:
    """
    Helper to save audit log, catching and logging exceptions.
    """
    try:
        save_audit_log(user_id, {"event_type": event_type, **event_data})
    except Exception as e:
        logger.error(f"Failed to save audit log for user {user_id}: {e}", exc_info=True)


def log_command(
    user_id: str,
    command_text: str,
    memory_sources: Optional[list[str]] = None,
    capability_flags: Optional[Dict[str, bool]] = None,
) -> None:
    """
    Logs a command invoked by the user.
    """
    event_data = {
        "command_text": command_text,
        "memory_sources": memory_sources or [],
        "capability_flags": capability_flags or {},
    }
    _log(user_id, "command_invoked", event_data)


def log_tool_call(
    user_id: str,
    tool_name: str,
    tool_args: Dict[str, Any],
    tool_result: Any,
) -> None:
    """
    Logs the execution of a tool.
    Redacts sensitive arguments like 'manifesto' content.
    """
    # Redact sensitive payloads
    if "manifesto" in tool_args:
        tool_args["manifesto"] = "[REDACTED]"

    event_data = {
        "tool_name": tool_name,
        "tool_args": tool_args,
        "tool_result": str(tool_result),  # Ensure result is a string
    }
    _log(user_id, "tool_call", event_data)


def log_retrieval(
    user_id: str,
    retrieval_query: str,
    retrieval_results: list[str],
    source: str,
) -> None:
    """
    Logs a retrieval operation from archive or scratch memory.
    """
    event_data = {
        "source": source,
        "retrieval_query": retrieval_query,
        "retrieval_results": retrieval_results,
    }
    _log(user_id, "retrieval_operation", event_data)
