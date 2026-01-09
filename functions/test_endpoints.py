#!/usr/bin/env python3
"""
Integration tests for HTTP endpoints.

Tests the webhook endpoint with various commands to ensure:
1. No 500 errors
2. Correct status codes and content types
3. Command routing works correctly
4. Auth/command parsing behaves as expected

Run from the functions directory: python3 test_endpoints.py
"""

import json
import os
import sys
from unittest.mock import Mock, patch, MagicMock
from typing import Any, Dict

# Set up test environment before imports
os.environ["TELEGRAM_TOKEN"] = "test_token_123"
os.environ["FIRESTORE_EMULATOR_HOST"] = "127.0.0.1:8080"
os.environ["GCLOUD_PROJECT"] = "demo-project"

from main import telegram_webhook
from router import route_update


class MockRequest:
    """Mock Flask/Functions Framework request object."""
    
    def __init__(self, method: str = "POST", json_data: Dict[str, Any] = None, args: Dict[str, str] = None):
        self.method = method
        self._json_data = json_data or {}
        self.args = args or {}
    
    def get_json(self, silent: bool = False) -> Dict[str, Any]:
        return self._json_data


def create_telegram_update(text: str, user_id: int = 123456, chat_id: int = 123456) -> Dict[str, Any]:
    """Create a mock Telegram update payload."""
    return {
        "update_id": 12345,
        "message": {
            "message_id": 1,
            "from": {
                "id": user_id,
                "is_bot": False,
                "first_name": "Test",
                "username": "testuser"
            },
            "chat": {
                "id": chat_id,
                "first_name": "Test",
                "username": "testuser",
                "type": "private"
            },
            "date": 1609459200,
            "text": text
        }
    }


def test_router():
    """Test the router with all commands."""
    print("\n=== Testing Router ===")
    
    test_cases = [
        # (input, expected_intent, description)
        ("/start", "start", "start command"),
        ("/help", "help", "help command"),
        ("/manual", "manual", "manual command"),
        ("/list", "list_tasks", "list command"),
        ("/recall", "recall", "recall command"),
        ("/scratch", "scratch", "scratch command"),
        ("/memory", "memory", "memory command"),
        ("/add task", "add_task", "add command with payload"),
        ("/done 1", "done_task", "done command with payload"),
        ("/unknown", "unknown_command", "unknown command"),
        ("plain text", "chat", "plain text message"),
    ]
    
    all_passed = True
    for text, expected_intent, description in test_cases:
        result = route_update(text)
        intent = result["intent"]
        
        if intent == expected_intent:
            print(f"  ✓ {description:30} -> {intent}")
        else:
            print(f"  ✗ {description:30} -> {intent} (expected {expected_intent})")
            all_passed = False
    
    return all_passed


def test_webhook_health_check():
    """Test webhook health check endpoint."""
    print("\n=== Testing Webhook Health Check ===")
    
    # Test GET request
    req = MockRequest(method="GET")
    response = telegram_webhook(req)
    
    if response.status_code == 200:
        print("  ✓ GET request returns 200")
    else:
        print(f"  ✗ GET request returns {response.status_code} (expected 200)")
        return False
    
    # Test ping parameter
    req = MockRequest(method="POST", args={"ping": "1"})
    response = telegram_webhook(req)
    
    if response.status_code == 200:
        print("  ✓ Ping parameter returns 200")
    else:
        print(f"  ✗ Ping parameter returns {response.status_code} (expected 200)")
        return False
    
    return True


@patch('main.agent')
@patch('telegram.Bot')
@patch('main.send_message_safe')
def test_webhook_commands(mock_send_safe, mock_bot_class, mock_agent):
    """Test webhook with various command payloads."""
    print("\n=== Testing Webhook Commands ===")
    
    # Mock the Bot class to return a mock instance
    mock_bot_instance = MagicMock()
    mock_bot_class.return_value = mock_bot_instance
    
    # Mock send_message_safe to be synchronous
    mock_send_safe.return_value = None
    
    # Mock agent response
    mock_agent.generate_response_with_tools.return_value = "Test response"
    
    test_commands = [
        ("/start", "start command should not crash"),
        ("/help", "help command should not crash"),
        ("/manual", "manual command should not crash"),
        ("/list", "list command should not crash"),
        ("/recall", "recall command should not crash"),
        ("/scratch", "scratch command should not crash"),
        ("/memory", "memory command should not crash"),
        ("/add Buy milk", "add command should not crash"),
        ("/done 1", "done command should not crash"),
        ("regular message", "chat message should not crash"),
    ]
    
    all_passed = True
    for command, description in test_commands:
        try:
            update_data = create_telegram_update(command)
            req = MockRequest(method="POST", json_data=update_data)
            
            response = telegram_webhook(req)
            
            # Webhook should always return 200 to Telegram to prevent retry storms
            if response.status_code == 200:
                print(f"  ✓ {description:40} (200)")
            else:
                print(f"  ✗ {description:40} ({response.status_code})")
                all_passed = False
        except Exception as e:
            print(f"  ✗ {description:40} (Exception: {e})")
            all_passed = False
    
    return all_passed


@patch('main.agent')
@patch('telegram.Bot')
@patch('main.send_message_safe')
def test_webhook_error_handling(mock_send_safe, mock_bot_class, mock_agent):
    """Test webhook error handling."""
    print("\n=== Testing Webhook Error Handling ===")
    
    # Mock the Bot class
    mock_bot_instance = MagicMock()
    mock_bot_class.return_value = mock_bot_instance
    mock_send_safe.return_value = None
    
    all_passed = True
    
    # Test empty body
    try:
        req = MockRequest(method="POST", json_data={})
        response = telegram_webhook(req)
        if response.status_code == 200:
            print("  ✓ Empty body returns 200")
        else:
            print(f"  ✗ Empty body returns {response.status_code}")
            all_passed = False
    except Exception as e:
        print(f"  ✗ Empty body handling failed: {e}")
        all_passed = False
    
    # Test malformed JSON (will be caught by get_json)
    try:
        req = MockRequest(method="POST", json_data=None)
        response = telegram_webhook(req)
        if response.status_code == 200:
            print("  ✓ Malformed JSON returns 200")
        else:
            print(f"  ✗ Malformed JSON returns {response.status_code}")
            all_passed = False
    except Exception as e:
        print(f"  ✗ Malformed JSON handling failed: {e}")
        all_passed = False
    
    # Test non-message update (e.g., channel post)
    try:
        update_data = {"update_id": 12345, "channel_post": {"text": "test"}}
        req = MockRequest(method="POST", json_data=update_data)
        response = telegram_webhook(req)
        if response.status_code == 200:
            print("  ✓ Non-message update returns 200")
        else:
            print(f"  ✗ Non-message update returns {response.status_code}")
            all_passed = False
    except Exception as e:
        print(f"  ✗ Non-message update handling failed: {e}")
        all_passed = False
    
    return all_passed


@patch('main.agent')
@patch('telegram.Bot')
@patch('main.send_message_safe')
def test_safe_mode_routing(mock_send_safe, mock_bot_class, mock_agent):
    """Test that safe mode properly handles commands."""
    print("\n=== Testing Safe Mode Routing ===")
    
    # Mock the Bot class
    mock_bot_instance = MagicMock()
    mock_bot_class.return_value = mock_bot_instance
    mock_send_safe.return_value = None
    
    # Force safe mode
    with patch('main.is_safe_mode', return_value=True):
        all_passed = True
        
        # Test that safe mode handles /list
        try:
            with patch('tools.get_manifesto', return_value="Test manifesto"):
                with patch('tools.get_pending_tasks', return_value=[]):
                    update_data = create_telegram_update("/list")
                    req = MockRequest(method="POST", json_data=update_data)
                    response = telegram_webhook(req)
                    
                    if response.status_code == 200:
                        print("  ✓ Safe mode handles /list command")
                    else:
                        print(f"  ✗ Safe mode /list returns {response.status_code}")
                        all_passed = False
        except Exception as e:
            print(f"  ✗ Safe mode /list failed: {e}")
            all_passed = False
        
        return all_passed


def main():
    """Run all tests."""
    print("=" * 60)
    print("Integration Tests for HTTP Endpoints")
    print("=" * 60)
    
    results = []
    
    # Test router
    results.append(("Router", test_router()))
    
    # Test health check
    results.append(("Health Check", test_webhook_health_check()))
    
    # Test command handling
    results.append(("Command Handling", test_webhook_commands()))
    
    # Test error handling
    results.append(("Error Handling", test_webhook_error_handling()))
    
    # Test safe mode
    results.append(("Safe Mode", test_safe_mode_routing()))
    
    # Summary
    print("\n" + "=" * 60)
    print("Test Summary")
    print("=" * 60)
    
    all_passed = True
    for name, passed in results:
        status = "✓ PASSED" if passed else "✗ FAILED"
        print(f"  {name:30} {status}")
        if not passed:
            all_passed = False
    
    print("=" * 60)
    
    if all_passed:
        print("✓ All tests passed!")
        return 0
    else:
        print("✗ Some tests failed!")
        return 1


if __name__ == "__main__":
    sys.exit(main())
