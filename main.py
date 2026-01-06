import os
import asyncio
from fastapi import FastAPI, Request
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
from database import Database
from llm_service import LLMService
from scheduler import SchedulerService
import uvicorn
from contextlib import asynccontextmanager

# Load environment variables (locally)
from dotenv import load_dotenv
load_dotenv()

# Initialize services
db = Database()
llm = LLMService(db)
scheduler = SchedulerService(db, llm)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    scheduler.start()

    # Initialize Telegram Webhook if needed here,
    # but usually handled by external config or separate script.
    # We will assume webhook is set manually or via a setup script.

    yield
    # Shutdown
    # scheduler.shutdown()

app = FastAPI(lifespan=lifespan)

@app.get("/")
def health_check():
    return {"status": "ok", "db_connected": db.is_connected()}

@app.post("/webhook")
async def telegram_webhook(request: Request):
    """
    Handle incoming Telegram updates.
    """
    try:
        data = await request.json()
        update = Update.de_json(data, None) # We don't have the bot instance here easily attached to context unless we use Application

        # We need to process this update.
        # Since we are using FastAPI as the webhook receiver, we can process manually or pass to PTB Application.
        # Constructing a PTB Application just to process update might be heavy but is standard.
        # Alternatively, simpler logic for just messages:

        if update.message and update.message.text:
            chat_id = update.message.chat.id
            user_id = update.message.from_user.id
            username = update.message.from_user.username or ""
            text = update.message.text

            # 1. Upsert User
            # Check if user exists first to avoid constant writes? Upsert is fine.
            db.upsert_user(user_id, username)

            # 2. Log User Message
            db.log_message(user_id, 'user', text)

            # 3. Generate Response
            response_text = await llm.generate_response(user_id, text)

            # 4. Send Response (using direct HTTP or PTB Bot instance)
            if scheduler.bot:
                await scheduler.bot.send_message(chat_id=chat_id, text=response_text)

                # 5. Log Assistant Message
                db.log_message(user_id, 'assistant', response_text)

        return {"status": "ok"}
    except Exception as e:
        print(f"Error processing webhook: {e}")
        return {"status": "error", "message": str(e)}

if __name__ == "__main__":
    # For local testing
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
