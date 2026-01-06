import os
import google.generativeai as genai
from typing import List, Dict, Any
from database import Database
import json

class LLMService:
    def __init__(self, db: Database):
        self.db = db
        api_key = os.environ.get("GEMINI_API_KEY")
        if api_key:
            genai.configure(api_key=api_key)
            self.model = genai.GenerativeModel('gemini-pro')
        else:
            self.model = None

    def _get_system_prompt(self, manifesto: str = "") -> str:
        base_prompt = (
            "You are a ruthless but empathetic Chief of Staff. Your goal is to keep the user aligned with their 'Manifesto'. "
            "RULES:\n"
            "1. Be concise. No 'I hope you are well'.\n"
            "2. If the user is drifting, steer them back to their top priority.\n"
            "3. Use 'Canonical Implementation' style: precise, actionable steps.\n"
            "4. If the user lists a task, add it to the DB. If they finish it, mark it done.\n"
            "5. You can execute tools by outputting a JSON block at the end of your message. "
            "Format: ```json\n{\"action\": \"add_task\", \"payload\": {\"description\": \"...\"}}\n``` "
            "or ```json\n{\"action\": \"mark_done\", \"payload\": {\"description_fragment\": \"...\"}}\n```\n"
            "or ```json\n{\"action\": \"update_manifesto\", \"payload\": {\"manifesto\": \"...\"}}\n```"
        )
        if manifesto:
            base_prompt += f"\n\nUSER MANIFESTO: {manifesto}"
        else:
            base_prompt += "\n\nThe user has not set a Manifesto yet. Ask them what their main 'North Star' goal is."

        return base_prompt

    async def generate_response(self, user_id: int, user_message: str) -> str:
        if not self.model:
            return "LLM Service not configured (missing API Key)."

        # 1. Fetch Context
        user_data = self.db.get_user(user_id)
        manifesto = user_data.get('manifesto') if user_data else None
        history = self.db.get_recent_messages(user_id, limit=10)

        # 2. Construct Prompt
        # Gemini Pro is stateless via API unless using ChatSession, but here we rebuild context manually to include system prompt effectively or use history.
        # We'll construct a list of contents.

        system_instruction = self._get_system_prompt(manifesto)

        # Convert history to Gemini format if possible, or just append to a large prompt.
        # Gemini API supports history in `start_chat`.

        chat_history = []
        # Prepend system instruction as the first part of the context or "user" message if system role not fully supported in this SDK version as distinct from content.
        # Actually, let's just use a direct generate_content with a constructed prompt for simplicity and control,
        # or use start_chat with history.

        # Mapping roles: 'user' -> 'user', 'assistant' -> 'model'
        for msg in history:
            role = 'user' if msg['role'] == 'user' else 'model'
            # simple filter for valid roles
            if role == 'user' or role == 'model':
                chat_history.append({'role': role, 'parts': [msg['content']]})

        # Start chat with history
        chat = self.model.start_chat(history=chat_history)

        # Send new message with system prompt injection (trick: prepend system prompt to the latest message or assume the model 'knows' via context).
        # Since we can't easily set a "system" message in `history` for `start_chat` in some versions, we'll prepend it to the current message
        # or rely on the fact that we can just prompt it.

        # Better approach for "System Prompt" with Gemini: Prepend to the very first message?
        # Or just prepend to the current message if it's stateless?
        # `start_chat` maintains state in the object.
        # But we are rebuilding state from DB each time (stateless bot).
        # So we should re-instantiate chat with history every time.

        full_message = f"SYSTEM INSTRUCTIONS:\n{system_instruction}\n\nUSER MESSAGE:\n{user_message}"

        try:
            response = chat.send_message(full_message)
            response_text = response.text

            # 3. Check for Tool Actions (JSON parsing)
            # Simple heuristic parsing
            if "```json" in response_text:
                import re
                json_match = re.search(r"```json\n(.*?)\n```", response_text, re.DOTALL)
                if json_match:
                    try:
                        action_data = json.loads(json_match.group(1))
                        action = action_data.get("action")
                        payload = action_data.get("payload", {})

                        if action == "add_task":
                            self.db.add_task(user_id, payload.get("description"))
                            # response_text += "\n[System: Task added]" # Optional feedback
                        elif action == "mark_done":
                            self.db.mark_task_done_by_description(user_id, payload.get("description_fragment"))
                            # response_text += "\n[System: Task marked done]"
                        elif action == "update_manifesto":
                            self.db.update_manifesto(user_id, payload.get("manifesto"))
                            # response_text += "\n[System: Manifesto updated]"

                        # Clean up the JSON from the user-facing response?
                        # The prompt says "Generate a response". Maybe we should hide the JSON.
                        response_text = response_text.replace(json_match.group(0), "").strip()

                    except json.JSONDecodeError:
                        pass # Failed to parse tool call

            return response_text
        except Exception as e:
            return f"Error interacting with LLM: {str(e)}"

    async def generate_push_message(self, user_id: int) -> str:
        if not self.model: return ""

        user_data = self.db.get_user(user_id)
        if not user_data: return ""

        manifesto = user_data.get('manifesto')
        if not manifesto: return "" # Don't push if no manifesto? Or prompt to set one?

        pending_tasks = self.db.get_pending_tasks(user_id)
        task_list = "\n".join([f"- {t['description']}" for t in pending_tasks])
        task_count = len(pending_tasks)

        prompt = (
            f"You are the Chief of Staff. It is 8 AM. \n"
            f"User Manifesto: {manifesto}\n"
            f"Pending Tasks ({task_count}):\n{task_list}\n\n"
            "Generate a message: 'It is 8 AM. Your main goal is [Manifesto]. You have [Count] open loops. "
            "The most critical one seems to be [Task X]. Suggestions on how to kill it before 10 AM?'"
        )

        try:
            response = self.model.generate_content(prompt)
            return response.text
        except Exception as e:
            return f"Error generating push: {str(e)}"
