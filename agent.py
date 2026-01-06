import os
from google import genai
from google.genai import types
from tools import TOOL_MAP, TOOL_DEFINITIONS, get_manifesto, get_pending_tasks

class Agent:
    def __init__(self):
        self.api_key = os.environ.get("GEMINI_API_KEY")
        if not self.api_key:
            print("Warning: GEMINI_API_KEY not set.")

        self.client = genai.Client(api_key=self.api_key)
        self.model = "gemini-2.0-flash" # Or gemini-1.5-pro, using flash for speed/cost in demo

        # System instructions
        self.system_instruction = (
            "You are a proactive Executive Coach. Your goal is to help the user achieve their 'Manifesto'. "
            "You have access to tools to manage their tasks and manifesto. "
            "ALWAYS check the manifesto if you don't know it. "
            "If the user adds a task, save it. "
            "If the user completes a task, mark it done. "
            "Be concise, direct, and helpful. No fluff."
        )

    def generate_response_with_tools(self, user_id: str, message_text: str) -> str:
        """
        Executes the Agent Loop:
        1. Sends user message + tools to LLM.
        2. If LLM requests tool calls, executes them.
        3. Sends tool results back to LLM.
        4. Returns final text response.
        """
        if not self.client:
            return "Error: LLM client not initialized."

        # We construct the chat history or context.
        # For this stateless implementation, we'll just send the current message
        # but in a real app we'd fetch history from DB.

        # Define tools configuration
        tools_config = [types.Tool(function_declarations=[
            types.FunctionDeclaration(**td) for td in TOOL_DEFINITIONS
        ])]

        # Start a chat session (stateless for this function call, but we simulate a turn)
        # We need to manually handle the turn if we want to loop tool calls.
        # simpler to use the `generate_content` with tools.

        conversation = []
        conversation.append(types.Content(
            role="user",
            parts=[types.Part.from_text(text=message_text)]
        ))

        config = types.GenerateContentConfig(
            tools=tools_config,
            system_instruction=self.system_instruction,
            automatic_function_calling=types.AutomaticFunctionCallingConfig(
                disable=False,
                maximum_remote_calls=5 # Allow multi-step
            )
        )

        # However, the SDK's `automatic_function_calling` might handle the loop for us if we provide the callables?
        # The Python SDK for `google-genai` (v1/new) supports automatic function calling if we pass the functions themselves?
        # Actually, let's look at how to bind functions.
        # If we pass definitions, we might need to handle execution manually or use the `tools` arg with actual functions if supported.
        # The `google-genai` library documentation says we can pass python functions directly to `tools`.

        # Let's try passing the python functions directly if possible, to simplify.
        # If not, we fall back to manual loop.
        # Given I defined `TOOL_MAP` and `TOOL_DEFINITIONS`, I'll use the manual loop control or the automatic one if I can verify it works.
        # The simplest robust way with the new SDK is to let it handle it if I pass the functions.

        # Re-import functions to pass them directly
        from tools import get_manifesto, set_manifesto, add_task, get_pending_tasks, complete_task

        my_tools = [get_manifesto, set_manifesto, add_task, get_pending_tasks, complete_task]

        try:
            # We need to wrap the tools to inject user_id if the LLM doesn't provide it reliably?
            # The LLM is instructed to provide user_id.

            # The SDK expects the tool functions to match the signature called by the model.

            chat = self.client.chats.create(
                model=self.model,
                config=types.GenerateContentConfig(
                    tools=my_tools,
                    system_instruction=self.system_instruction,
                    automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=False)
                )
            )

            # We must inject user_id into the context so the model knows it.
            # Or we rely on the model to pass `user_id` which it infers from the context we give it.
            # We can tell the model "The current user_id is {user_id}".

            response = chat.send_message(f"User ID: {user_id}\nMessage: {message_text}")
            return response.text

        except Exception as e:
            return f"Agent Error: {str(e)}"

    def generate_morning_briefing(self, user_id: str) -> str:
        """
        Proactive function: Fetches data and generates a briefing.
        """
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
            response = self.client.models.generate_content(
                model=self.model,
                contents=prompt
            )
            return response.text
        except Exception as e:
            return f"Briefing Error: {str(e)}"
