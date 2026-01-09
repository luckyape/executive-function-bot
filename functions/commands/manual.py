import os

def get_manual_text():
    """
    Reads and returns the content of the user manual.
    """
    # Try multiple possible paths for the manual
    possible_paths = [
        # Development: functions/commands/../.. -> repo root
        os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "USER_MANUAL.md"),
        # Firebase deployment: might be at the functions level
        os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "USER_MANUAL.md"),
        # Firebase deployment: might be copied to the same directory
        os.path.join(os.path.dirname(os.path.abspath(__file__)), "USER_MANUAL.md"),
    ]
    
    for manual_path in possible_paths:
        try:
            with open(manual_path, "r", encoding="utf-8") as f:
                return f.read()
        except FileNotFoundError:
            continue
    
    # If none of the paths worked, return error
    return "Error: The user manual is currently unavailable."
