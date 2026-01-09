import os

def get_manual_text():
    """
    Reads and returns the content of the user manual.
    """
    try:
        # Construct path relative to this script's location
        script_dir = os.path.dirname(os.path.abspath(__file__))
        manual_path = os.path.join(script_dir, "..", "..", "USER_MANUAL.md")
        with open(manual_path, "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        return "Error: The user manual is currently unavailable."
