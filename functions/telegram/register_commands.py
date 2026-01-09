import asyncio
import os
import sys

# Add the parent directory to the Python path to allow for absolute imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from telegram import Bot, BotCommand
from config import get_config

async def main():
    """
    Registers commands with Telegram.
    Run this script locally:
    `python functions/telegram/register_commands.py`
    """
    token = get_config("TELEGRAM_TOKEN")
    if not token:
        print("Error: TELEGRAM_TOKEN not found in environment variables.")
        return

    bot = Bot(token=token)
    commands = [
        BotCommand("start", "Begin your journey and set your Manifesto."),
        BotCommand("help", "Get help and see examples."),
        BotCommand("manual", "Read the full user manual."),
        BotCommand("add", "Add a new task."),
        BotCommand("list", "List your pending tasks."),
        BotCommand("done", "Complete a task."),
        BotCommand("scratch", "Manage your scratchpad."),
        BotCommand("recall", "Recall memories and notes."),
        BotCommand("archive", "Interact with your archive."),
        BotCommand("memory", "Manage your memory settings."),
    ]
    await bot.set_my_commands(commands)
    print("Commands registered successfully.")

if __name__ == "__main__":
    asyncio.run(main())
