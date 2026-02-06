"""Financial Expert Agent — ReAct-style agent with OpenAI function calling."""

import json
import os
from datetime import date
from typing import Any, AsyncGenerator, Generator

from dotenv import load_dotenv
from openai import OpenAI

from agent_prompts import build_system_prompt, FALLBACK_MESSAGE
from agent_tools import TOOL_SCHEMAS, execute_tool
from data_store import DataStore
from utils import setup_logger

load_dotenv()
logger = setup_logger(__name__, "agent.log")

# Token limits
MAX_CONTEXT_TOKENS = 40000
SUMMARIZE_THRESHOLD = 35000


class FinancialExpertAgent:
    """ReAct-style financial expert agent using OpenAI function calling."""

    def __init__(
        self,
        store: DataStore,
        model: str = "gpt-4o",
        temperature: float = 0.3,
    ):
        self.store = store
        self.model = model
        self.temperature = temperature
        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

        # Get context for system prompt
        counts = store.get_table_counts()
        sectors = store.get_all_sectors()

        # Get latest price date
        row = store.conn.execute("SELECT MAX(date) as latest FROM prices").fetchone()
        latest_date = row["latest"] if row else None

        self.system_prompt = build_system_prompt(
            total_stocks=counts.get("stocks", 500),
            total_sectors=len(sectors),
            latest_price_date=latest_date,
        )

        # Conversation history
        self.messages: list[dict] = []
        self._token_count = 0

    def _estimate_tokens(self, text: str) -> int:
        """Rough token estimate (4 chars per token on average)."""
        return len(text) // 4

    def _should_summarize(self) -> bool:
        """Check if we need to summarize conversation history."""
        total = sum(self._estimate_tokens(json.dumps(m)) for m in self.messages)
        return total > SUMMARIZE_THRESHOLD

    def _summarize_history(self) -> None:
        """Summarize old messages to save context space."""
        if len(self.messages) < 6:
            return

        # Keep system message and last 4 turns
        to_summarize = self.messages[:-4]
        recent = self.messages[-4:]

        # Create summary
        summary_text = "Previous conversation summary:\n"
        for msg in to_summarize:
            role = msg.get("role", "")
            content = msg.get("content", "")
            if role == "user":
                summary_text += f"- User asked: {content[:100]}...\n"
            elif role == "assistant" and content:
                summary_text += f"- Assistant provided analysis on: {content[:100]}...\n"

        self.messages = [
            {"role": "system", "content": f"{self.system_prompt}\n\n{summary_text}"}
        ] + recent

        logger.info(f"Summarized conversation history. New length: {len(self.messages)}")

    def get_response(self, user_message: str, conversation_id: str | None = None) -> str:
        """Get a complete response (non-streaming)."""
        response_parts = []
        for chunk in self.stream_response_sync(user_message, conversation_id):
            if chunk.get("type") == "text":
                response_parts.append(chunk.get("content", ""))
            elif chunk.get("type") == "error":
                return f"Error: {chunk.get('content', 'Unknown error')}"

        return "".join(response_parts)

    def stream_response_sync(
        self, user_message: str, conversation_id: str | None = None
    ) -> Generator[dict, None, None]:
        """Stream response chunks synchronously."""
        # Check if we need to summarize
        if self._should_summarize():
            self._summarize_history()

        # Add user message
        if not self.messages:
            self.messages.append({"role": "system", "content": self.system_prompt})
        self.messages.append({"role": "user", "content": user_message})

        max_iterations = 10  # Prevent infinite loops
        iteration = 0

        while iteration < max_iterations:
            iteration += 1

            try:
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=self.messages,
                    tools=TOOL_SCHEMAS,
                    tool_choice="auto",
                    temperature=self.temperature,
                    stream=True,
                )

                # Collect the full response
                full_content = ""
                tool_calls = []
                current_tool_call = None

                for chunk in response:
                    delta = chunk.choices[0].delta if chunk.choices else None
                    if not delta:
                        continue

                    # Handle text content
                    if delta.content:
                        full_content += delta.content
                        yield {"type": "text", "content": delta.content}

                    # Handle tool calls
                    if delta.tool_calls:
                        for tc in delta.tool_calls:
                            if tc.index is not None:
                                # New or continuing tool call
                                while len(tool_calls) <= tc.index:
                                    tool_calls.append({
                                        "id": "",
                                        "function": {"name": "", "arguments": ""}
                                    })
                                current = tool_calls[tc.index]

                                if tc.id:
                                    current["id"] = tc.id
                                if tc.function:
                                    if tc.function.name:
                                        current["function"]["name"] = tc.function.name
                                    if tc.function.arguments:
                                        current["function"]["arguments"] += tc.function.arguments

                finish_reason = chunk.choices[0].finish_reason if chunk.choices else None

                # If we have tool calls, execute them
                if tool_calls:
                    # Add assistant message with tool calls
                    assistant_msg = {"role": "assistant", "content": full_content or None}
                    assistant_msg["tool_calls"] = [
                        {
                            "id": tc["id"],
                            "type": "function",
                            "function": tc["function"]
                        }
                        for tc in tool_calls
                        if tc["id"]
                    ]
                    self.messages.append(assistant_msg)

                    # Execute each tool call
                    for tc in tool_calls:
                        if not tc["id"]:
                            continue

                        tool_name = tc["function"]["name"]
                        try:
                            args = json.loads(tc["function"]["arguments"])
                        except json.JSONDecodeError:
                            args = {}

                        yield {
                            "type": "tool_call",
                            "tool": tool_name,
                            "arguments": args
                        }

                        logger.info(f"Executing tool: {tool_name} with args: {args}")

                        # Execute the tool
                        result = execute_tool(self.store, tool_name, args)

                        yield {
                            "type": "tool_result",
                            "tool": tool_name,
                            "result_preview": str(result)[:200]
                        }

                        # Add tool result to messages
                        self.messages.append({
                            "role": "tool",
                            "tool_call_id": tc["id"],
                            "content": json.dumps(result, default=str)
                        })

                    # Continue the loop to get the final response
                    continue

                else:
                    # No tool calls, we're done
                    if full_content:
                        self.messages.append({
                            "role": "assistant",
                            "content": full_content
                        })
                    break

            except Exception as e:
                logger.error(f"Agent error: {e}")
                yield {"type": "error", "content": str(e)}
                break

    async def stream_response(
        self, user_message: str, conversation_id: str | None = None
    ) -> AsyncGenerator[dict, None]:
        """Async wrapper for streaming (for FastAPI SSE)."""
        for chunk in self.stream_response_sync(user_message, conversation_id):
            yield chunk

    def reset_conversation(self) -> None:
        """Clear conversation history."""
        self.messages = []


# Singleton for CLI usage
_agent_instance: FinancialExpertAgent | None = None


def get_agent(store: DataStore, model: str = "gpt-4o") -> FinancialExpertAgent:
    """Get or create the agent instance."""
    global _agent_instance
    if _agent_instance is None:
        _agent_instance = FinancialExpertAgent(store, model=model)
    return _agent_instance
