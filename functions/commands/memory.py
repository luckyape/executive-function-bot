from __future__ import annotations

from db.user_settings_repo import get_memory_mode, set_memory_mode, MemoryMode


def handle_memory_command(user_id: str, text: str) -> str:
    """
    Handles the /memory command.
    - /memory: Shows current mode.
    - /memory <mode>: Sets a new mode.

    Modes come from MemoryMode enum (expected values: off, hot, projects, strict).
    """
    parts = (text or "").strip().lower().split()
    if not parts:
        return "Usage: /memory [off|hot|projects|strict]"

    if parts[0] != "/memory":
        return "Invalid command."

    # /memory
    if len(parts) == 1:
        current_mode = get_memory_mode(user_id)
        # current_mode should be MemoryMode; if repo returns a string, this still works
        value = current_mode.value if hasattr(current_mode, "value") else str(current_mode)
        return f"Memory mode is currently set to: {value}"

    # /memory <mode>
    if len(parts) == 2:
        new_mode_str = parts[1]
        try:
            new_mode = MemoryMode(new_mode_str)
        except ValueError:
            valid_modes = ", ".join([mode.value for mode in MemoryMode])
            return f"Invalid memory mode '{new_mode_str}'. Valid modes are: {valid_modes}"

        ok = set_memory_mode(user_id, new_mode)
        if ok:
            return f"Memory mode set to: {new_mode.value}"
        return "Failed to set memory mode."

    return "Usage: /memory [off|hot|projects|strict]"