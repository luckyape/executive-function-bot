from ..db.user_settings_repo import get_memory_mode, set_memory_mode, MemoryMode

def handle_memory_command(user_id: str, text: str) -> str:
    """
    Handles the /memory command.
    - /memory: Shows current mode.
    - /memory [mode]: Sets a new mode.
    """
    parts = text.strip().lower().split()
    command = parts[0]

    if command != "/memory":
        return "Invalid command."

    # /memory - Show current mode
    if len(parts) == 1:
        current_mode = get_memory_mode(user_id)
        return f"Memory mode is currently set to: {current_mode.value}"

    # /memory [mode] - Set new mode
    elif len(parts) == 2:
        new_mode_str = parts[1]
        try:
            new_mode = MemoryMode(new_mode_str)
            if set_memory_mode(user_id, new_mode):
                return f"Memory mode set to: {new_mode.value}"
            else:
                return "Failed to set memory mode."
        except ValueError:
            valid_modes = ", ".join([mode.value for mode in MemoryMode])
            return f"Invalid memory mode '{new_mode_str}'. Valid modes are: {valid_modes}"

    else:
        return "Usage: /memory [off|hot|projects|strict]"
