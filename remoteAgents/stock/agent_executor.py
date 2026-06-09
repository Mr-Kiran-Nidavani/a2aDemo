"""
StockAgentExecutor — A2A SDK AgentExecutor for the Stock agent.

Receives a task via RequestContext, calls get_stock(), formats with LLM,
publishes the result via TaskUpdater, and marks the task complete.
"""
import os
from uuid import uuid4

from dotenv import load_dotenv
from litellm import acompletion

from a2a.server.agent_execution.agent_executor import AgentExecutor
from a2a.server.agent_execution.context import RequestContext
from a2a.server.events.event_queue import EventQueue
from a2a.server.tasks.task_updater import TaskUpdater
from a2a.types import Part, TaskState

from remoteAgents.stock.stock_tool import get_stock

load_dotenv()


class StockAgentExecutor(AgentExecutor):
    """Handles stock queries end-to-end using the A2A TaskUpdater pattern."""

    async def execute(self, context: RequestContext, event_queue: EventQueue) -> None:
        task_updater = TaskUpdater(
            event_queue=event_queue,
            task_id=context.task_id,
            context_id=context.context_id,
        )

        # Mark task as working
        await task_updater.update_status(TaskState.TASK_STATE_WORKING)

        # Extract user text
        try:
            user_text = context.message.parts[0].text or ""
        except (AttributeError, IndexError):
            user_text = ""

        # Extract ticker symbol and call the mock stock tool
        symbol = self._extract_symbol(user_text)
        stock_data = get_stock(symbol)

        # Format response using LLM
        formatted = await self._format_with_llm(user_text, stock_data)

        # Publish result and complete
        result_message = task_updater.new_agent_message(parts=[Part(text=formatted)])
        await task_updater.complete(message=result_message)

    async def cancel(self, context: RequestContext, event_queue: EventQueue) -> None:
        task_updater = TaskUpdater(
            event_queue=event_queue,
            task_id=context.task_id,
            context_id=context.context_id,
        )
        await task_updater.cancel()

    # ── Private helpers ───────────────────────────────────────────────────────

    def _extract_symbol(self, text: str) -> str:
        """
        Best-effort ticker extraction from natural language.
        Falls back to 'AAPL' if nothing recognised.
        """
        known_symbols = [
            "AAPL", "TSLA", "GOOGL", "MSFT", "AMZN",
            "NVDA", "META", "NFLX", "RELIANCE", "TCS", "INFY",
        ]
        upper = text.upper()
        for sym in known_symbols:
            if sym in upper:
                return sym
        # Try last all-caps word as a fallback
        words = text.split()
        for word in reversed(words):
            cleaned = word.strip("?.,!").upper()
            if cleaned.isalpha() and len(cleaned) >= 2:
                return cleaned
        return "AAPL"

    async def _format_with_llm(self, query: str, stock_data: dict) -> str:
        """Sends stock data to the LLM and returns a natural-language 3-line response."""
        if stock_data.get("status") == "not_found":
            return stock_data.get("message", "Stock data not available.")

        system_prompt = (
            "You are a concise stock analyst. "
            "Always respond in exactly 3 lines:\n"
            "Line 1: Current price and today's change.\n"
            "Line 2: Sentiment (Bullish / Bearish / Neutral) with one reason.\n"
            "Line 3: Simple verdict — Good Buy, Hold, or Avoid — with one short reason.\n"
            "Keep it brief, clear, and jargon-free."
        )
        user_prompt = (
            f"User asked: '{query}'\n\n"
            f"Stock data: {stock_data}\n\n"
            "Please format this into a 3-line stock analysis."
        )

        response = await acompletion(
            model="openai/gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            api_key=os.getenv("OPENAI_API_KEY"),
        )
        return response.choices[0].message.content.strip()
