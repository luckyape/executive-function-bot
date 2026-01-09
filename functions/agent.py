from __future__ import annotations

import logging

from google import genai
from google.genai import types
from google.api_core import exceptions

from tools import get_manifesto, get_pending_tasks
from config import get_config, is_safe_mode
from context_builder import build_context
from audit.logger import log_command

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
        self,
        user_id: str,
        message_text: str,
        intent: str | list[str] | None = "chat",
        capabilities: list[str] | None = None,
    ) -> str:
        """
        Backward-compatible parameter handling:
        - New style: (user_id, message_text, intent="chat", capabilities=[...])
        - Old style: (user_id, message_text, capabilities=[...])  -> detected if intent is a list
        """
        # Back-compat: third positional might be capabilities (list[str]) from older call sites
        if isinstance(intent, list):
            capabilities = intent
            intent = "chat"

        if intent is None:
            intent = "chat"
        if capabilities is None:
            capabilities = []

        client = self._get_client()
        if not client:
            return "LLM is unavailable right now. I can still add/list/complete tasks."

        # Import tool functions (keep local to reduce import/cycle risk)
        from tools import set_manifesto, add_task, complete_task

        # Base tools for all intents
        enabled_tools = [
            get_manifesto,
            set_manifesto,
            add_task,
            get_pending_tasks,
            complete_task,
        ]

        # Gated tools (only enabled when capability flag is present)
        if "recall" in capabilities:
            from tools import recall
            enabled_tools.append(recall)
        if "scratch" in capabilities:
            from tools import scratch
            enabled_tools.append(scratch)
        if "archive" in capabilities:
            from tools import archive
            enabled_tools.append(archive)

        # Audit trail (best-effort; never blocks response generation)
        try:
            capability_flags = {
                "safe_mode": bool(is_safe_mode()),
                "intent": intent,
                "capabilities": list(capabilities),
            }
            memory_sources = [t.__name__ for t in enabled_tools]

            log_command(
                user_id,
                message_text,
                memory_sources=memory_sources,
                capability_flags=capability_flags,
            )
        except Exception as e:
            logger.warning(f"audit log_command failed: {e}", exc_info=True)

        try:
            # Context is helpful but not required; fail open.
            context = ""
            try:
                context = build_context(user_id) or ""
            except Exception as e:
                logger.warning(f"build_context failed: {e}", exc_info=True)
                context = ""

            prompt_parts: list[str] = [f"User ID: {user_id}"]

            # Only include intent when it's not plain chat (keeps normal chat clean)
            if intent and intent != "chat":
                prompt_parts.append(f"Intent: {intent}")

            if context:
                prompt_parts.append(f"Context:\n{context}")

            prompt_parts.append(f"Message: {message_text}")
            prompt = "\n\n".join(prompt_parts)

            chat = client.chats.create(
                model=self.model,
                config=types.GenerateContentConfig(
                    tools=enabled_tools,
                    system_instruction=self.system_instruction,
                    automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=False),
                ),
            )

            response = chat.send_message(prompt)
            return response.text

        except exceptions.ResourceExhausted as e:
            logger.warning(f"Gemini 429/ResourceExhausted: {e}")
            return "LLM is rate-limited right now. I can still add/list/complete tasks. Try again shortly."

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

        context = ""
        try:
            context = build_context(user_id) or ""
        except Exception as e:
            logger.warning(f"build_context failed (morning briefing): {e}", exc_info=True)
            context = ""

        prompt = (
            f"{context}\n\n"
            "Based on this context, write a 1-sentence 'Kick in the ass' message."
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