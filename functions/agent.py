import logging
from google import genai
from google.genai import types
from google.api_core import exceptions

from tools import get_manifesto, get_pending_tasks
from config import get_config

logger = logging.getLogger(__name__)


class Agent:
    def __init__(self):
        self.api_key = get_config("GEMINI_API_KEY")
        self.client = None
        self.model = "gemini-2.0-flash"

        self.system_instruction = (
            "You are a proactive Executive Coach. Your goal is to help the user achieve their 'Manifesto'. "
            "You have access to tools to manage their tasks and manifesto. "
            "ALWAYS check the manifesto if you don't know it. "
            "If the user adds a task, save it. "
            "If the user completes a task, mark it done. "
            "Be concise, direct, and helpful. No fluff."
        )

    def _get_client(self):
        if self.client:
            return self.client

        if not self.api_key:
            self.api_key = get_config("GEMINI_API_KEY")

        if not self.api_key:
            logger.warning("GEMINI_API_KEY not set. Agent will fail to generate responses.")
            return None

        try:
            self.client = genai.Client(api_key=self.api_key)
        except Exception as e:
            logger.error(f"Failed to initialize GenAI Client: {e}", exc_info=True)
            return None

        return self.client

    def generate_response_with_tools(
        self, user_id: str, message_text: str, capabilities: list[str] | None = None
    ) -> str:
        if capabilities is None:
            capabilities = []
        client = self._get_client()
        if not client:
            return "LLM is unavailable right now. I can still add/list/complete tasks."

        # Standard tools available in chat
        from tools import get_manifesto, set_manifesto, add_task, get_pending_tasks, complete_task
        my_tools = [get_manifesto, set_manifesto, add_task, get_pending_tasks, complete_task]

        # Add recall tool if capability is present
        if "recall" in capabilities:
            from tools import recall
            my_tools.append(recall)

        try:
            chat = client.chats.create(
                model=self.model,
                config=types.GenerateContentConfig(
                    tools=my_tools,  # if this ever breaks, switch to tools=_tools_config
                    system_instruction=self.system_instruction,
                    automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=False),
                ),
            )
            response = chat.send_message(f"User ID: {user_id}\nMessage: {message_text}")
            return response.text

        except exceptions.ResourceExhausted as e:
            logger.warning(f"Gemini 429/ResourceExhausted: {e}")
            return "LLM is rate-limited right now. I can still add/list/complete tasks. Try again in ~30s."

        except exceptions.GoogleAPICallError as e:
            logger.error(f"Gemini API Call Error: {e}", exc_info=True)
            return "I hit a temporary issue talking to Gemini. Try again shortly (tasks still work)."

        except Exception as e:
            logger.error(f"Gemini General Exception: {e}", exc_info=True)
            return "I encountered a temporary issue with my brain. Please try again."

    def generate_morning_briefing(self, user_id: str) -> str:
        client = self._get_client()
        if not client:
            return ""

        manifesto = get_manifesto(str(user_id))
        pending_tasks = get_pending_tasks(str(user_id))
        task_list = "\n".join([f"- {t['description']}" for t in pending_tasks])

        prompt = (
            f"User ID: {user_id}\n"
            f"Manifesto: {manifesto}\n"
            f"Pending Tasks:\n{task_list}\n\n"
            "Based on these tasks and this goal, write a 1-sentence 'Kick in the ass' message."
        )

        try:
            response = client.models.generate_content(model=self.model, contents=prompt)
            return response.text

        except exceptions.ResourceExhausted as e:
            logger.warning(f"Morning Briefing Skipped (Rate Limit): {e}")
            return ""

        except Exception as e:
            logger.error(f"Briefing Error: {e}", exc_info=True)
            return ""
