## Deployment

```bash
firebase deploy --only functions:telegram_webhook
```

## Verification

**A) Health Check**

```bash
curl -s "https://us-central1-executive-function-coaching.cloudfunctions.net/telegram_webhook?ping=1"
```
*Expected output: `ok`*

**B) Telegram Webhook Status**

Replace `<YOUR_TELEGRAM_TOKEN>` with your bot's token.

```bash
curl -s "https://api.telegram.org/bot<YOUR_TELEGRAM_TOKEN>/getWebhookInfo"
```
*After a successful message, the `last_error_message` field should be absent.*

**C) Test Message**

Send "hi" to your bot in the Telegram app.

*Expected reply: "Hello. I am alive."*

**D) Check Logs**

```bash
gcloud functions logs read telegram_webhook --region=us-central1 --limit=50
```
*Look for any crashes or error messages. If the token is missing, you should see "Telegram token not set".*
