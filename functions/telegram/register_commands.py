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
        BotCommand("help", "Show help"),
        BotCommand("list", "List pending tasks"),
        BotCommand("start", "Start the bot and set your manifesto"),
        BotCommand("manual", "Show the user manual"),
    ]
    await bot.set_my_commands(commands)
    print("Commands registered successfully.")

if __name__ == "__main__":
    asyncio.run(main())
