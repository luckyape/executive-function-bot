# The Life OS Telegram Bot — User Manual

## What this app does
The Life OS bot is a Telegram-based executive coach. It helps you:

- Define and remember a **Manifesto** (your main goal).
- Capture and manage **tasks**.
- Keep quick notes in a **scratchpad**.
- Search your **archive** for past memories.
- Receive a daily **morning briefing**.

## Getting started
1. Open the bot in Telegram and send `/start`.
2. When prompted, send a short statement of your **Manifesto** (your main goal).

If you skip `/start`, you can still send your Manifesto as your first message—once it is stored, the bot will reference it in future replies.

## Core task workflow
The bot understands simple text commands to manage tasks:

- **Add a task**: `add Buy groceries`
- **List tasks**: `list` (or `/list`)
- **Complete a task**:
  - By number: `done #3`
  - By text fragment: `done Buy groceries`

When you run `list`, tasks are shown in order with `#` numbers. Use those numbers with `done #N` to complete quickly.

## Scratchpad (quick notes)
Use the scratchpad when you want to capture snippets without turning them into tasks.

- **Add a note**: `/scratch add Remember to ask about budget`
- **Show recent notes**: `/scratch show` (or `/scratch show 5` for the last 5)
- **Clear all notes**: `/scratch clear`
- **Promote a note to a task**:
  - `/scratch promote <scratchId> <hot|archive> [tag/project]`

The promote command turns a scratch entry into a task. Use `hot` to keep it immediately actionable, or `archive` to file it with a project label.

## Memory modes
The bot can use different levels of context in its replies. Check or set the memory mode with:

- **Show current mode**: `/memory`
- **Set a mode**: `/memory off|hot|projects|strict`

Modes:
- `off`: No memory context.
- `hot`: Only your Manifesto.
- `projects`: Manifesto + pending tasks.
- `strict`: Same as `projects` today, but reserved for the most context-heavy mode.

## Recall from archive
Use `/recall <query>` to search your archive for old notes or summaries.

Example:
```
/recall onboarding checklist
```

## Morning briefing
Every day at **08:00 UTC**, the bot sends a one-sentence “kick in the ass” briefing based on your current context.

## Safe Mode (limited brain)
If the AI model is unavailable, the bot enters a Safe Mode and still supports:

- `add <task>`
- `list` / `/list`
- `done <fragment>` or `done #N`

In Safe Mode, your **Manifesto** will be set if it’s missing, and task commands will still work.

---

If something feels off, try `/help` to see example commands and verify the bot is responding.
