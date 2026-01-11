from __future__ import annotations

import inspect
import json
import logging
from typing import Any, Dict, List, Optional, Union, get_args, get_origin

from openai import APIConnectionError, APIError, OpenAI, RateLimitError

from tools import get_manifesto, get_pending_tasks
from config import get_config, is_safe_mode
from context_builder import build_context
from audit.logger import log_command

logger = logging.getLogger(__name__)


class Agent:
    def __init__(self):
        self.api_key = get_config("OPENAI_API_KEY")
        self.client = None
        self.model = "gpt-4o"

        self.system_instruction = (
            "You are a supportive, pragmatic friend-coach and expert guide for this Life OS app (Version 3.0). "
            "You understand ADHD/autism/executive dysfunction patterns. You help without shame, pressure, or moralizing. "
            "Your job is: (1) help the user advance their Manifesto, and (2) help them use the system in a way that fits their brain.\n\n"
        
            "Neurodivergence-friendly interaction rules:\n"
            "- Assume good intent. Never scold. No guilt language.\n"
            "- Reduce overwhelm: offer at most 2–3 options at a time; default to the simplest next step.\n"
            "- Be concrete: suggest the next action in 1–2 sentences, then stop unless asked.\n"
            "- Ask lightweight clarifying questions only when necessary. Prefer a reasonable guess + easy correction.\n"
            "- If the user is stuck, do a tiny plan: one step now, one step next.\n"
            "- Use permission-based coaching: ask 'Want a quick suggestion?' before giving process advice.\n"
            "- Mirror tone: calm when stressed, lightly playful when invited.\n"
            "- Briefly acknowledge completions (one line max). No pep-talks.\n\n"
        
            "App Capabilities & Security Model:\n"
            "- Strict Commands (`/list`) are for fast, deterministic execution. Contextual Commands (`/list grocery items`) are AI-assisted.\n"
            "- Tools are unlocked dynamically based on user intent and command usage.\n"
            "- Never claim you executed a tool unless you actually did. If a tool is unavailable, say so plainly.\n\n"
        
            "Tools:\n"
            "- Tasks: add, list, complete. Shortcut: 'done #3' completes task #3 from the list.\n"
            "- Scratchpad: quick notes (/scratch add, show, clear). Promote them to tasks when helpful.\n"
            "- Memory: adjust context depth (/memory off|hot|projects|strict).\n"
            "- Recall: search the archive (/recall).\n\n"
        
            "Behavior priorities:\n"
            "1) Execute: use tools to manage tasks + manifesto. If user adds a task, save it. If they complete one, mark it done.\n"
            "2) Guide: answer questions about features/workflows using plain language and examples.\n"
            "3) Coach (light touch): if you notice friction/inefficiency, offer ONE better pattern briefly, with an example.\n"
            "4) Output style: concise, direct, kind. Avoid walls of text. Short paragraphs. Plan text only.\n\n"
        
            "ND-aware heuristics (use silently):\n"
            "- If the user brain-dumps, offer to convert it into 3–7 tasks and ask if they want that.\n"
            "- If the user asks for motivation, offer either (a) a 30-second starter step or (b) a 5-minute plan, and let them pick.\n"
            "- If the user is bouncing topics, help pick a single 'now' focus and park the rest in scratch.\n"
        )
    def _get_client(self):
        if self.client:
            return self.client

        if not self.api_key:
            self.api_key = get_config("OPENAI_API_KEY")

        if not self.api_key:
            logger.warning("OPENAI_API_KEY not set. Agent will fail to generate responses.")
            return None

        try:
            self.client = OpenAI(api_key=self.api_key)
        except Exception as e:
            logger.error(f"Failed to initialize OpenAI Client: {e}", exc_info=True)
            return None

        return self.client

    def _extract_function_calls(self, response: Any) -> List[Any]:
        calls: List[Any] = []
        outputs = getattr(response, "output", None) or []
        for item in outputs:
            if getattr(item, "type", None) == "function_call":
                calls.append(item)
        return calls

    def _args_to_dict(self, fc_args: Any) -> Dict[str, Any]:
        if fc_args is None:
            return {}
        if isinstance(fc_args, dict):
            return fc_args
        try:
            if isinstance(fc_args, str):
                return json.loads(fc_args)
        except json.JSONDecodeError:
            return {}
        except Exception:
            return {}
        return {}

    def _format_tool_output(self, payload: Dict[str, Any]) -> str:
        try:
            return json.dumps(payload, ensure_ascii=False)
        except Exception:
            return json.dumps({"error": "Failed to serialize tool output."})

    def _annotation_to_schema(self, annotation: Any) -> Dict[str, Any]:
        if annotation in [int]:
            return {"type": "integer"}
        if annotation in [float]:
            return {"type": "number"}
        if annotation in [bool]:
            return {"type": "boolean"}
        if annotation in [list, List]:
            return {"type": "array", "items": {}}
        if annotation in [dict, Dict]:
            return {"type": "object"}
        origin = get_origin(annotation)
        if origin is list:
            return {"type": "array", "items": {}}
        if origin is dict:
            return {"type": "object"}
        if origin is Union:
            args = [arg for arg in get_args(annotation) if arg is not type(None)]
            if args:
                return self._annotation_to_schema(args[0])
        return {"type": "string"}

    def _tool_to_schema(self, tool: Any) -> Dict[str, Any]:
        sig = inspect.signature(tool)
        properties: Dict[str, Any] = {}
        required: List[str] = []
        for name, param in sig.parameters.items():
            if name == "user_id":
                continue
            annotation = param.annotation if param.annotation is not inspect._empty else str
            properties[name] = self._annotation_to_schema(annotation)
            if param.default is inspect._empty:
                required.append(name)
        description = (tool.__doc__ or "").strip()
        tool_name = getattr(tool, "__name__", None) or getattr(tool, "__qualname__", None)
        if not tool_name:
            tool_name = f"tool_{id(tool)}"
            logger.warning("Tool name missing; using fallback %s", tool_name)
        elif not isinstance(tool_name, str):
            tool_name = str(tool_name)
        return {
            "type": "function",
            "name": tool_name,
            "description": description,
            "parameters": {
                "type": "object",
                "properties": properties,
                "required": required,
            },
        }

    def _get_response_text(self, response: Any) -> str:
        output_text = getattr(response, "output_text", None)
        if output_text:
            return output_text
        outputs = getattr(response, "output", None) or []
        for item in outputs:
            if getattr(item, "type", None) == "message":
                content = getattr(item, "content", None) or []
                parts = [getattr(part, "text", "") for part in content if getattr(part, "type", "") == "output_text"]
                if parts:
                    return "".join(parts)
        return str(response)

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
            tool_specs = [self._tool_to_schema(tool) for tool in whitelisted_tool_map.values()]
            response = client.responses.create(
                model=self.model,
                input=[
                    {"role": "system", "content": self.system_instruction},
                    {"role": "user", "content": prompt},
                ],
                tools=tool_specs,
            )

            # Manual tool call dispatch loop (supports chained tool calls)
            max_tool_rounds = 3
            for _ in range(max_tool_rounds):
                function_calls = self._extract_function_calls(response)
                if not function_calls:
                    break

                tool_outputs: List[Dict[str, Any]] = []
                for function_call in function_calls:
                    tool_name = getattr(function_call, "name", None) or ""
                    tool_func = whitelisted_tool_map.get(tool_name)

                    if not tool_func:
                        logger.warning(f"Model attempted to call non-whitelisted tool: {tool_name}")
                        tool_outputs.append(
                            {
                                "type": "function_call_output",
                                "call_id": getattr(function_call, "call_id", ""),
                                "output": self._format_tool_output(
                                    {"error": f"Tool '{tool_name}' is not available."}
                                ),
                            }
                        )
                        continue

                    args = self._args_to_dict(getattr(function_call, "arguments", None))

                    # Ensure user_id is always present unless explicitly provided
                    if "user_id" not in args:
                        args["user_id"] = user_id

                    try:
                        result = tool_func(**args)
                        tool_outputs.append(
                            {
                                "type": "function_call_output",
                                "call_id": getattr(function_call, "call_id", ""),
                                "output": self._format_tool_output({"result": result}),
                            }
                        )
                    except Exception as e:
                        logger.error(f"Tool '{tool_name}' failed: {e}", exc_info=True)
                        tool_outputs.append(
                            {
                                "type": "function_call_output",
                                "call_id": getattr(function_call, "call_id", ""),
                                "output": self._format_tool_output(
                                    {"error": f"Tool '{tool_name}' failed: {type(e).__name__}"}
                                ),
                            }
                        )

                # Send tool results back to the model in a single message
                response = client.responses.create(
                    model=self.model,
                    input=tool_outputs,
                    previous_response_id=getattr(response, "id", None),
                    tools=tool_specs,
                )

            # If we still have function calls after max rounds, fail closed.
            if self._extract_function_calls(response):
                return "I hit an internal tool-call loop limit. Try rephrasing or simplifying the request."

            return self._get_response_text(response)

        except RateLimitError as e:
            logger.warning(f"OpenAI 429/RateLimitError: {e}")
            return "LLM is rate-limited right now. I can still add/list/complete tasks. Try again shortly."

        except (APIError, APIConnectionError) as e:
            logger.error(f"OpenAI API Error: {e}", exc_info=True)
            return "I hit a temporary issue talking to the LLM API. Try again shortly (tasks still work)."
        except Exception as e:
            # Propagate unknown errors so main.py can trigger Safe Mode
            logger.error(f"OpenAI General Exception: {e}", exc_info=True)
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
            "Based on this context, write a 1-sentence supportive nudge that is practical and non-shaming. Offer one concrete next step."
        )

        try:
            response = client.responses.create(
                model=self.model,
                input=[
                    {"role": "system", "content": self.system_instruction},
                    {"role": "user", "content": prompt},
                ],
            )
            return self._get_response_text(response)

        except RateLimitError as e:
            logger.warning(f"Morning Briefing Skipped (Rate Limit): {e}")
            return ""

        except Exception as e:
            logger.error(f"Briefing Error: {e}", exc_info=True)
            return ""
