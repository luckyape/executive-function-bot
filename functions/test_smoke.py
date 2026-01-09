#!/usr/bin/env python3
"""
Smoke tests for HTTP endpoints - minimal validation that endpoints don't crash.

Run from the functions directory: python3 test_smoke.py
"""

import sys
from router import route_update


def test_router_smoke():
    """Smoke test: ensure router doesn't crash on any input."""
    print("=== Router Smoke Test ===")
    
    test_cases = [
        # Core commands
        ("/start", "start"),
        ("/help", "help"),
        ("/manual", "manual"),
        
        # Tasking commands
        ("/list", "list_tasks"),
        ("/add task", "add_task"),
        ("/done 1", "done_task"),
        
        # Memory commands
        ("/recall", "recall"),
        ("/scratch", "scratch"),
        ("/scratch show", "scratch"),
        ("/scratch add note", "scratch"),
        ("/memory", "memory"),
        ("/archive", "archive"),
        
        # Unknown/chat
        ("/unknown", "unknown_command"),
        ("hello", "chat"),
        ("", "chat"),
    ]
    
    all_passed = True
    for text, expected_intent in test_cases:
        try:
            result = route_update(text)
            intent = result.get("intent")
            
            if intent == expected_intent:
                print(f"  ✓ '{text:25}' -> {intent}")
            else:
                print(f"  ✗ '{text:25}' -> {intent} (expected {expected_intent})")
                all_passed = False
        except Exception as e:
            print(f"  ✗ '{text:25}' crashed: {e}")
            all_passed = False
    
    return all_passed


def test_command_imports():
    """Smoke test: ensure all command handlers can be imported."""
    print("\n=== Command Import Smoke Test ===")
    
    imports_to_test = [
        ("commands.list", "handle_list_command"),
        ("commands.recall", "handle_recall_command"),
        ("commands.scratch", "handle_scratch_command"),
        ("commands.manual", "get_manual_text"),
        ("commands.memory", "handle_memory_command"),
        ("commands.add", "handle_add_command"),
        ("commands.done", "handle_done_command"),
        ("commands.archive", "handle_archive_command"),
        ("commands.help", "get_help_text"),
        ("telegram_utils", "send_message"),
        ("telegram_utils", "send_message_safe"),
    ]
    
    all_passed = True
    for module_name, attr_name in imports_to_test:
        try:
            module = __import__(module_name, fromlist=[attr_name])
            attr = getattr(module, attr_name)
            print(f"  ✓ {module_name}.{attr_name}")
        except Exception as e:
            print(f"  ✗ {module_name}.{attr_name}: {e}")
            all_passed = False
    
    return all_passed


def test_manual_text():
    """Smoke test: ensure manual text can be loaded."""
    print("\n=== Manual Text Smoke Test ===")
    
    try:
        from commands.manual import get_manual_text
        text = get_manual_text()
        
        if "Error:" in text:
            print(f"  ✗ Manual text returned error: {text}")
            return False
        elif len(text) > 100:
            print(f"  ✓ Manual text loaded ({len(text)} chars)")
            return True
        else:
            print(f"  ✗ Manual text too short ({len(text)} chars)")
            return False
    except Exception as e:
        print(f"  ✗ Manual text loading crashed: {e}")
        return False


def main():
    """Run all smoke tests."""
    print("=" * 60)
    print("Smoke Tests for HTTP Endpoints")
    print("=" * 60)
    print()
    
    results = []
    
    # Test router
    results.append(("Router", test_router_smoke()))
    
    # Test command imports
    results.append(("Command Imports", test_command_imports()))
    
    # Test manual text
    results.append(("Manual Text", test_manual_text()))
    
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
        print("✓ All smoke tests passed!")
        return 0
    else:
        print("✗ Some smoke tests failed!")
        return 1


if __name__ == "__main__":
    sys.exit(main())
