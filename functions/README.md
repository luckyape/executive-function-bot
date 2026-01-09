# Telegram Bot Commands

This document explains how to register the bot's commands with Telegram.

## Registering Commands

To register the bot's commands, run the following script from the root of the repository:

```bash
python functions/telegram/register_commands.py
```

This will register the commands with Telegram, making them available in the bot's command menu.

## Development Conventions

### Import Convention

**All imports must use absolute paths from the `/functions` directory root.**

Firebase Functions executes code from the `/functions` directory, which means:
- `functions/` is the root of the Python module namespace
- Top-level modules include: `commands`, `db`, `telegram_utils`, `firestore_client`, `tools`, etc.
- There is no parent package above these modules

**✅ CORRECT - Use absolute imports:**
```python
from db.scratch_repo import ScratchRepo
from telegram_utils import send_message
from firestore_client import db
```

**❌ INCORRECT - Do not use relative imports:**
```python
from ..db.scratch_repo import ScratchRepo  # Will fail!
from ..telegram_utils import send_message   # Will fail!
```

**Why this matters:**
Relative imports (using `..` to go up a directory) fail when modules are imported as top-level packages. This causes webhook crashes with the error: `ImportError: attempted relative import beyond top-level package`.

### Testing Import Compliance

To verify all files follow the import convention, run:

```bash
cd functions
python3 test_imports.py
```

This test checks that no files use relative imports and will fail if any are found.
