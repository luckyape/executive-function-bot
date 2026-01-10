from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

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
        self.model = "gemini-3-flash-preview"

        self.system_instruction = (
            "You are a proactive Executive Coach and expert guide for this Life OS app (Version 3.0-flash). "
            "Your goal is to help the user achieve their 'Manifesto' while mastering the system.\n\n"
            "App Capabilities & Security Model:\n"
            "- Core Principle: Strict Commands (`/list`) are for fast, deterministic execution. Contextual Commands (`/list grocery items`) are for AI-assisted execution.\n"
            "- Tools are unlocked dynamically based on user intent and command usage.\n\n"
            "Tools:\n"
            "- Tasks: Add, list, and complete tasks. Shortcut: 'done #3' completes task #3 from the list.\n"
            "- Scratchpad: Quick notes (/scratch add, show, clear). Promote them to tasks if needed.\n"
            "- Memory: Adjust context depth (/memory off|hot|projects|strict).\n"
            "- Recall: Search the archive (/recall).\n\n"
            "Behaviors:\n"
            "1. Execute: Use tools to manage tasks and manifesto. If the user adds a task, save it. If they complete one, mark it done.\n"
            "2. Guide: Answer questions about app features and workflows.\n"
            "3. Coach: If you detect inefficient usage (like typing full task names instead of numbers), briefly suggest the better way.\n"
            "4. Style: Be concise, direct, and non-interruptive. No fluff."
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

    def _extract_function_calls(self, response: Any) -> List[Any]:
        """
        Defensive extraction across SDK response shapes.
        Returns a list of function_call objects.
        """
        calls: List[Any] = []

        try:
            parts = getattr(response, "parts", None)

            # Some SDK shapes: response.candidates[0].content.parts
            if parts is None:
                cands = getattr(response, "candidates", None)
                if cands:
                    content = getattr(cands[0], "content", None)
                    parts = getattr(content, "parts", None)

            if not parts:
                return calls

            for p in parts:
                fc = getattr(p, "function_call", None)
                if fc:
                    calls.append(fc)
        except Exception:
            return calls

        return calls

    def _args_to_dict(self, fc_args: Any) -> Dict[str, Any]:
        if fc_args is None:
            return {}
        if isinstance(fc_args, dict):
            return fc_args
        # google genai often uses a proto-ish map that supports to_dict
        try:
            to_dict = getattr(type(fc_args), "to_dict", None)
            if callable(to_dict):
                return to_dict(fc_args)
        except Exception:
            pass
        # last-resort coercion
        try:
            return dict(fc_args)
        except Exception:
            return {}

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

        # Import tool functions locally to avoid import cycles
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

        # Strict whitelist for tool execution (even if the model asks for something else)
        whitelisted_tool_map = {tool.__name__: tool for tool in enabled_tools}

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

        # Build prompt (context is best-effort)
        context = ""
        try:
            context = build_context(user_id) or ""
        except Exception as e:
            logger.warning(f"build_context failed: {e}", exc_info=True)
            context = ""

        prompt_parts: list[str] = [f"User ID: {user_id}"]
        if intent and intent != "chat":
            prompt_parts.append(f"Intent: {intent}")
        if context:
            prompt_parts.append(f"Context:\n{context}")
        prompt_parts.append(f"Message: {message_text}")
        prompt = "\n\n".join(prompt_parts)

        try:
            chat = client.chats.create(
                model=self.model,
                config=types.GenerateContentConfig(
                    tools=list(whitelisted_tool_map.values()),
                    system_instruction=self.system_instruction,
                    # Strict mode: do NOT allow SDK to auto-execute tools.
                    automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True),
                ),
            )

            response = chat.send_message(prompt)

            # Manual tool call dispatch loop (supports chained tool calls)
            max_tool_rounds = 3
            for _ in range(max_tool_rounds):
                function_calls = self._extract_function_calls(response)
                if not function_calls:
                    break

                tool_response_parts: List[types.Part] = []
                for function_call in function_calls:
                    tool_name = getattr(function_call, "name", None) or ""
                    tool_func = whitelisted_tool_map.get(tool_name)

                    if not tool_func:
                        logger.warning(f"Model attempted to call non-whitelisted tool: {tool_name}")
                        tool_response_parts.append(
                            types.Part(
                                tool_response=types.ToolResponse(
                                    name=tool_name,
                                    response={"error": f"Tool '{tool_name}' is not available."},
                                )
                            )
                        )
                        continue

                    args = self._args_to_dict(getattr(function_call, "args", None))

                    # Ensure user_id is always present unless explicitly provided
                    if "user_id" not in args:
                        args["user_id"] = user_id

                    try:
                        result = tool_func(**args)
                        tool_response_parts.append(
                            types.Part(
                                tool_response=types.ToolResponse(
                                    name=tool_name,
                                    response={"result": result},
                                )
                            )
                        )
                    except Exception as e:
                        logger.error(f"Tool '{tool_name}' failed: {e}", exc_info=True)
                        tool_response_parts.append(
                            types.Part(
                                tool_response=types.ToolResponse(
                                    name=tool_name,
                                    response={"error": f"Tool '{tool_name}' failed: {type(e).__name__}"},
                                )
                            )
                        )

                # Send tool results back to the model in a single message
                response = chat.send_message(types.Content(parts=tool_response_parts))

            # If we still have function calls after max rounds, fail closed.
            if self._extract_function_calls(response):
                return "I hit an internal tool-call loop limit. Try rephrasing or simplifying the request."

            return getattr(response, "text", None) or str(response)

        except exceptions.ResourceExhausted as e:
            logger.warning(f"Gemini 429/ResourceExhausted: {e}")
            return "LLM is rate-limited right now. I can still add/list/complete tasks. Try again shortly."

        except exceptions.GoogleAPICallError as e:
            logger.error(f"Gemini API Call Error: {e}", exc_info=True)
            return "I hit a temporary issue talking to Gemini. Try again shortly (tasks still work)."

        except Exception as e:
            # Propagate unknown errors so main.py can trigger Safe Mode
            logger.error(f"Gemini General Exception: {e}", exc_info=True)
            raise e

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
            return getattr(response, "text", None) or ""

        except exceptions.ResourceExhausted as e:
            logger.warning(f"Morning Briefing Skipped (Rate Limit): {e}")
            return ""

        except Exception as e:
            logger.error(f"Briefing Error: {e}", exc_info=True)
            return ""
