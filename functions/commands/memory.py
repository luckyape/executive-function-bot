from db import user_settings_repo

VALID_MODES = ["off", "hot", "projects", "strict"]

def handle_memory_command(user_id: str, command_text: str) -> str:
    """
    Handles the /memory command.
    """
    parts = command_text.strip().split()
    if not parts:
        current_mode = user_settings_repo.get_memory_mode(user_id)
        return f"Current memory mode: {current_mode}. Use /memory <mode> to set."

    mode = parts[0].lower()
    if mode not in VALID_MODES:
        return f"Invalid mode. Valid modes are: {', '.join(VALID_MODES)}"

    user_settings_repo.set_memory_mode(user_id, mode)
    return f"Memory mode set to: {mode}"
