import os
import asyncio
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from database import Database
from llm_service import LLMService
from telegram import Bot

class SchedulerService:
    def __init__(self, db: Database, llm: LLMService):
        self.db = db
        self.llm = llm
        self.scheduler = AsyncIOScheduler()
        self.telegram_token = os.environ.get("TELEGRAM_TOKEN")
        self.bot = Bot(token=self.telegram_token) if self.telegram_token else None

    def start(self):
        # Schedule the job to run every day at 8 AM UTC (or handle timezones logic later)
        # For simplicity, we'll run at 8 AM UTC.
        # Ideally, we should check user timezones, but '8 AM Local' requires per-user scheduling or frequent checks.
        # A simple approach: Run every hour, check which users are at 8 AM in their timezone.

        self.scheduler.add_job(self.morning_push_routine, CronTrigger(minute=0)) # Run every hour
        self.scheduler.start()

    async def morning_push_routine(self):
        if not self.bot:
            print("Scheduler: Telegram Bot token not set.")
            return

        print("Running morning push routine...")
        # In a real production app, we would query users whose local time is 8 AM.
        # For this prototype, we'll iterate all users and assume UTC or just send it (to avoid complex timezone math right now).
        # Or let's try to do it right:
        # We need to know current UTC time.

        from datetime import datetime, timezone
        import pytz

        current_utc = datetime.now(timezone.utc)

        users = self.db.get_all_users()
        for user in users:
            user_tz_str = user.get('timezone', 'UTC')
            try:
                user_tz = pytz.timezone(user_tz_str)
                # Convert current UTC to user time
                user_time = current_utc.astimezone(user_tz)

                # Check if it's 8 AM (e.g., between 8:00 and 8:59, ensuring we only send once per day)
                # Since this runs every hour (minute=0), checking hour==8 is sufficient.
                if user_time.hour == 8:
                    await self.send_push_for_user(user['id'])

            except Exception as e:
                print(f"Error processing user {user['id']}: {e}")

    async def send_push_for_user(self, user_id: int):
        message = await self.llm.generate_push_message(user_id)
        if message:
            try:
                await self.bot.send_message(chat_id=user_id, text=message)
                self.db.log_message(user_id, 'assistant', message)
            except Exception as e:
                print(f"Failed to send push to {user_id}: {e}")
