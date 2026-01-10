
import unittest
from unittest.mock import patch, MagicMock
import json
import sys

# --- Mocks must be setup BEFORE importing main ---
sys.modules['firebase_admin'] = MagicMock()
sys.modules['firebase_admin.credentials'] = MagicMock()
sys.modules['firebase_admin.firestore'] = MagicMock()
sys.modules['openai'] = MagicMock()

# Mock the Agent class entirely
mock_agent_instance = MagicMock()
mock_agent_class = MagicMock(return_value=mock_agent_instance)
sys.modules['agent'] = MagicMock()
sys.modules['agent'].Agent = mock_agent_class

# Now we can safely import main
import main 
from main import telegram_webhook

class MockRequest:
    def __init__(self, method="GET", json_data=None, args=None):
        self.method = method
        self._json = json_data
        self.args = args or {}

    def get_json(self, silent=False):
        if self._json is None and not silent:
            raise ValueError("No JSON")
        return self._json

class TestEndpoints(unittest.TestCase):
    
    def setUp(self):
        # PATCH: Force TELEGRAM_TOKEN to be set so main.py checks pass
        # This fixes the "Config key 'TELEGRAM_TOKEN' not found" error in CI
        self.original_token = main.TELEGRAM_TOKEN
        main.TELEGRAM_TOKEN = "TEST_TOKEN"

    def tearDown(self):
        main.TELEGRAM_TOKEN = self.original_token

    def test_webhook_get(self):
        """Tests that GET requests to the webhook return 200 OK."""
        req = MockRequest(method="GET")
        response = telegram_webhook(req)
        self.assertEqual(response.status_code, 200)
        # Flask/Functions Framework response.response can be a list of bytes
        self.assertIn(b"ok", response.response)

    def test_webhook_empty_post(self):
        """Tests that an empty POST request is handled gracefully."""
        req = MockRequest(method="POST", json_data={})
        response = telegram_webhook(req)
        self.assertEqual(response.status_code, 200)

    def test_webhook_malformed_json(self):
        """Tests that a malformed JSON body is handled gracefully."""
        req = MockRequest(method="POST", json_data=None)
        response = telegram_webhook(req)
        self.assertEqual(response.status_code, 200)

    def test_start_command(self):
        """Tests the /start command."""
        data = {
            "update_id": 99999,
            "message": {
                "message_id": 1,
                "text": "/start",
                "chat": {
                    "id": 12345,
                    "type": "private"
                },
                "from": {
                    "id": 67890,
                    "first_name": "TestUser",
                    "is_bot": False
                },
                "date": 1678888888
            }
        }
        req = MockRequest(method="POST", json_data=data)
        
        with patch("main._send") as mock_send:
            response = telegram_webhook(req)
            self.assertEqual(response.status_code, 200)
            mock_send.assert_called_with(12345, "Welcome! Tell me your Manifesto (Goal).")

    def test_agent_failure_causes_safe_mode(self):
        """
        Tests that a failure in the agent's generate_response_with_tools method
        results in the fallback to Safe Mode.
        """
        print("\nRunning test_agent_failure_causes_safe_mode...")
        data = {
            "update_id": 88888,
            "message": {
                "message_id": 2,
                "text": "tell me a story",
                "chat": {
                    "id": 12345,
                    "type": "private"
                },
                "from": {
                    "id": 67890,
                    "first_name": "TestUser",
                    "is_bot": False
                },
                "date": 1678888889
            }
        }
        req = MockRequest(method="POST", json_data=data)

        # We need to mock the route_update to return 'chat' intent so it hits the agent
        with patch("main.route_update") as mock_route:
            mock_route.return_value = {"intent": "chat", "payload": "tell me a story"}
            
            # Mock the agent instance on the 'main' module specifically
            from main import agent
            with patch.object(agent, 'generate_response_with_tools', side_effect=Exception("LLM Brain Fart")):
                with patch("main._send") as mock_send:
                    # We also need to mock get_manifesto to prevent database calls in Safe Mode
                    with patch("tools.get_manifesto", return_value="My Goal"):
                        response = telegram_webhook(req)

                        # Check that the webhook still returns 200 OK
                        self.assertEqual(response.status_code, 200)

                        # Check if _send was called
                        self.assertTrue(mock_send.called, "main._send was not called")

                        # The Safe Mode handler sends the fallback message FIRST
                        sent_text = mock_send.call_args_list[0][0][1]
                        self.assertIn("LLM is busy right now, so I'm in Safe Mode", sent_text)
                        print("  ✓ Agent failure correctly triggered the 'Safe Mode' fallback message.")

    def test_critical_failure_causes_generic_error(self):
        """
        Tests that a failure BEFORE the agent (e.g. routing) triggers the
        'A critical error occurred' message.
        """
        print("\nRunning test_critical_failure_causes_generic_error...")
        data = {
            "update_id": 77777,
            "message": {
                "message_id": 3,
                "text": "hello",
                "chat": {
                    "id": 99999,
                    "type": "private"
                },
                "from": {
                    "id": 67890,
                    "first_name": "TestUser",
                    "is_bot": False
                },
                "date": 1678888890
            }
        }
        req = MockRequest(method="POST", json_data=data)

        # Force route_update to crash. This happens before Agent logic.
        with patch("main.route_update", side_effect=Exception("Routing Crashed")):
            with patch("main._send") as mock_send:
                response = telegram_webhook(req)

                self.assertEqual(response.status_code, 200)
                
                # Check if _send was called
                self.assertTrue(mock_send.called, "main._send was not called")
                
                sent_chat_id = mock_send.call_args[0][0]
                sent_text = mock_send.call_args[0][1]

                self.assertEqual(sent_chat_id, 99999)
                self.assertEqual(sent_text, "A critical error occurred.")
                print("  ✓ Critical failure correctly triggered the 'critical error' message.")

if __name__ == "__main__":
    unittest.main()
