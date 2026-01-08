import logging
from typing import Any, Dict, Optional

from db.audit_repo import save_audit_log

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
    Logs a command invoked by the user, redacting the raw text.
    """
    event_data = {
        "command_text": "[REDACTED]",  # Redact user input
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
    Redacts sensitive arguments and results to avoid storing PII.
    """
    # Redact sensitive payloads from arguments
    if tool_name == "set_manifesto":
        tool_args["manifesto"] = "[REDACTED]"
    if tool_name == "add_task":
        tool_args["description"] = "[REDACTED]"
    if tool_name == "complete_task":
        if "query" in tool_args:
            tool_args["query"] = "[REDACTED]"

    # Redact sensitive payloads from results
    redacted_result = ""
    if tool_name == "get_manifesto":
        redacted_result = "[REDACTED]"
    elif tool_name == "get_pending_tasks":
        # Result is a list of tasks, log the count instead.
        try:
            task_count = len(tool_result)
            redacted_result = f"Found {task_count} tasks."
        except TypeError:
            redacted_result = "Found 0 tasks."
    elif tool_name == "add_task":
        redacted_result = "Task added."
    elif tool_name == "complete_task":
        # Result can be one of many strings.
        if isinstance(tool_result, str) and tool_result.startswith("Task marked as done:"):
            redacted_result = "Task marked as done."
        else:
            redacted_result = "Task completion attempted."  # Generic for other cases
    else:
        # For other tools like set_manifesto, the result is a simple confirmation string.
        redacted_result = str(tool_result)

    event_data = {
        "tool_name": tool_name,
        "tool_args": tool_args,
        "tool_result": redacted_result,
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
        "retrieval_query": "[REDACTED]" if retrieval_query else "",
        "retrieval_results": retrieval_results,
        "num_results": len(retrieval_results),
    }
    _log(user_id, "retrieval_operation", event_data)
