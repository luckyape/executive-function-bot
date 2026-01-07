# The Life OS (Firebase + MCP Edition)

A proactive "Executive Coach" Telegram bot built on Firebase Cloud Functions and Google Gemini Pro using the MCP (Model Context Protocol) pattern for tools.

## Architecture

- **Backend**: Firebase Cloud Functions (2nd Gen) - Serverless Python.
- **Database**: Google Cloud Firestore (NoSQL).
- **Intelligence**: Google Gemini Pro (via `google-genai`).
- **Interface**: Telegram Bot API (Webhook).
- **Tooling**: MCP-style tool definitions defined in `tools.py` and consumed by the Agent.

## Features

1.  **Reactive Agent**: Responds to messages, automatically managing tasks and manifesto updates using tools (`add_task`, `complete_task`, `set_manifesto`).
2.  **Proactive Scheduler**: Runs every day at 08:00 UTC to send a "Kick in the ass" briefing based on your pending tasks and life goals.
3.  **NoSQL Data Structure**: Flexible user documents in Firestore.

## Prerequisites

- Python 3.11+
- Firebase CLI (`npm install -g firebase-tools`)
- A Firebase Project (Blaze plan required for external network calls to Telegram/Gemini).
- Telegram Bot Token.
- Gemini API Key.

## Setup

1.  **Install Dependencies**:
    ```bash
    pip install -r requirements.txt
    ```

2.  **Environment Variables**:
    Cloud Functions use `.env` or Secret Manager. For local testing, copy `.env.example`:
    ```bash
    cp .env.example .env
    ```
    Fill in `TELEGRAM_TOKEN` and `GEMINI_API_KEY`.

3.  **Firebase Init**:
    If you haven't already:
    ```bash
    firebase login
    firebase init functions
    ```
    (Select "Use existing project" and "Python").

## Deployment

1.  **Deploy Functions**:
    ```bash
    firebase deploy --only functions
    ```

2.  **Set Webhook**:
    After deployment, get the URL for `telegram_webhook` from the console output.
    Set the webhook:
    ```bash
    curl "https://api.telegram.org/bot<YOUR_TOKEN>/setWebhook?url=<YOUR_FUNCTION_URL>"
    ```

## Local Development & Emulation

### Using the Firebase Emulator
To run functions locally without connecting to the production Firestore:
1.  Start the emulator:
    ```bash
    firebase emulators:start
    ```
2.  Set the environment variable (if running python scripts directly outside the emulator context):
    ```bash
    export FIRESTORE_EMULATOR_HOST="127.0.0.1:8080"
    export GCLOUD_PROJECT="demo-project"
    ```

### Using Production Firestore Locally
If you want to connect to the real database from your local machine:
1.  Authenticate with Google Cloud:
    ```bash
    gcloud auth application-default login
    ```
2.  The code will automatically detect the credentials.

## Local Testing

To test the agent logic directly:
```python
from agent import Agent
a = Agent()
print(a.generate_response_with_tools("123", "Add a task to buy milk"))
```
