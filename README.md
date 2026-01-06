# The Executive Function Coach (Telegram Bot)

A proactive "Chief of Staff" Telegram bot that helps you stay aligned with your goals using an Event-Driven architecture and Google Gemini Pro.

## Features

- **Event-Driven Architecture**: Uses a scheduler to send unsolicited "Push" messages.
- **Context Aware**: Remembers the last 10 messages of conversation.
- **Task Management**: Automatically extracts tasks from conversation and tracks them in a Supabase database.
- **Morning Push**: Sends a morning briefing at 8 AM local time with your Manifesto and critical tasks.
- **Manifesto Alignment**: The "Brain" (LLM) constantly steers you back to your "North Star" goals.

## Tech Stack

- **Python 3.11+**
- **FastAPI**: Webhook handling.
- **Supabase**: PostgreSQL database for Users, Logs, and Tasks.
- **Google Gemini Pro**: LLM for generating responses.
- **APScheduler**: Background task scheduling.
- **python-telegram-bot**: Telegram API wrapper.

## Setup

1.  **Clone the repository**
2.  **Install dependencies**:
    ```bash
    pip install -r requirements.txt
    ```
3.  **Environment Variables**:
    Copy `.env.example` to `.env` and fill in the values:
    - `TELEGRAM_TOKEN`: From BotFather.
    - `GEMINI_API_KEY`: From Google AI Studio.
    - `SUPABASE_URL` & `SUPABASE_KEY`: From your Supabase project settings.

4.  **Database Schema**:
    Run the following SQL in your Supabase SQL Editor:

    ```sql
    -- Users Table
    CREATE TABLE users (
        id BIGINT PRIMARY KEY, -- Telegram User ID
        username TEXT,
        timezone TEXT DEFAULT 'UTC',
        manifesto TEXT, -- The user's "North Star" goals
        created_at TIMESTAMP DEFAULT NOW()
    );

    -- Conversation History (for Context)
    CREATE TABLE message_logs (
        id SERIAL PRIMARY KEY,
        user_id BIGINT REFERENCES users(id),
        role TEXT CHECK (role IN ('user', 'assistant', 'system')),
        content TEXT,
        created_at TIMESTAMP DEFAULT NOW()
    );

    -- Active Tasks (The "Open Loops")
    CREATE TABLE tasks (
        id SERIAL PRIMARY KEY,
        user_id BIGINT REFERENCES users(id),
        description TEXT,
        status TEXT DEFAULT 'pending', -- pending, done, blocked
        due_date TIMESTAMP,
        created_at TIMESTAMP DEFAULT NOW()
    );
    ```

## Deployment

This project includes a `Procfile` for deployment on platforms like Render or Railway.

1.  **Push to GitHub**.
2.  **Connect to Render/Railway**.
3.  **Set Environment Variables** in the dashboard.
4.  **Deploy**.
5.  **Set Webhook**:
    Once deployed, set your Telegram bot webhook to your deployed URL:
    `https://api.telegram.org/bot<YOUR_TOKEN>/setWebhook?url=https://<YOUR_APP_URL>/webhook`

## Usage

- Start chatting with the bot.
- Tell it your "Manifesto" (e.g., "My goal is to launch my startup by Q4").
- Add tasks naturally (e.g., "I need to email the investors").
- The bot will remind you of your goals and tasks at 8 AM.
