# Tests

This directory contains tests for the Life OS Telegram Bot.

## Test Files

### test_imports.py
Validates that all command modules use absolute imports (no relative imports).

```bash
cd functions
python3 test_imports.py
```

### test_smoke.py
Quick smoke tests to validate:
- Router maps all commands correctly
- All command handlers can be imported
- Manual text can be loaded

```bash
cd functions
python3 test_smoke.py
```

### test_endpoints.py
Comprehensive integration tests for HTTP endpoints:
- Webhook health checks
- Command routing and handling
- Error handling
- Safe mode routing

**Note:** These tests require proper mocking of Firebase and Telegram services. Some tests may show errors/warnings about missing credentials, but should still pass if the webhook returns 200.

```bash
cd functions
python3 test_endpoints.py
```

## Running All Tests

```bash
cd functions
python3 test_imports.py && python3 test_smoke.py
```

## Test Coverage

The tests validate:

1. **Command Recognition** - All documented commands (/start, /help, /manual, /list, /recall, /scratch, /memory, /add, /done) are properly recognized by the router
2. **No Import Errors** - All command modules can be imported without errors
3. **Error Handling** - Endpoints return 200 OK even on errors (prevents Telegram retry storms)
4. **Manual Loading** - User manual can be loaded from multiple possible paths
5. **Safe Mode** - Deterministic commands work when LLM is unavailable

## Test Results Interpretation

- **Router Tests**: Ensure slash commands map to the correct intent
- **Import Tests**: Ensure no circular imports or missing dependencies
- **Smoke Tests**: Quick validation that nothing is fundamentally broken
- **Integration Tests**: More thorough validation of webhook behavior

## Notes

- Integration tests mock external services (Firebase, Telegram API)
- Database errors in integration tests are expected and handled correctly
- The webhook should always return 200 OK to Telegram, even on internal errors
- Commands that need database access will log errors but not crash the webhook
