def get_manual_text():
    """
    Reads and returns the content of the user manual.
    """
    try:
        with open("USER_MANUAL.md", "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        return "Error: The user manual is currently unavailable."
