"""
StockAgentExecutor — A2A SDK AgentExecutor for the Stock agent.

Follows the official A2A SDK pattern (from the docs):
  1. Create or retrieve task, enqueue it
  2. Update status → WORKING
  3. Execute business logic (tool call + LLM format)
  4. Add result as an artifact
  5. Update status → COMPLETED
"""
import os

from dotenv import load_dotenv
from litellm import acompletion

from a2a.server.agent_execution.agent_executor import AgentExecutor
from a2a.server.agent_execution.context import RequestContext
from a2a.server.events.event_queue import EventQueue
from a2a.server.tasks.task_updater import TaskUpdater
from a2a.types import TaskState
from a2a.helpers import (
    get_message_text,
    new_task_from_user_message,
    new_text_message,
    new_text_part,
)

from remoteAgents.stock.stock_tool import get_stock

load_dotenv()


class StockAgentExecutor(AgentExecutor):
    """Handles stock queries following the official A2A executor pattern."""

    async def execute(self, context: RequestContext, event_queue: EventQueue) -> None:
        # Step 1: Create or retrieve task and enqueue it
        if context.current_task:
            task = context.current_task
        else:
            task = new_task_from_user_message(context.message)
            await event_queue.enqueue_event(task)

        task_updater = TaskUpdater(
            event_queue=event_queue,
            task_id=task.id,
            context_id=task.context_id,
        )

        # Step 2: Signal working
        await task_updater.update_status(
            state=TaskState.TASK_STATE_WORKING,
            message=new_text_message("Looking up stock data..."),
        )

        # Step 3: Extract ticker and call the stock tool
        user_text = get_message_text(context.message) or ""
        symbol = self._extract_symbol(user_text)
        stock_data = get_stock(symbol)

        # Step 4: Format with LLM and add as artifact
        formatted = await self._format_with_llm(user_text, stock_data)
        await task_updater.add_artifact(
            parts=[new_text_part(text=formatted, media_type="text/plain")],
            name="stock_result",
        )

        # Step 5: Mark completed
        await task_updater.update_status(
            state=TaskState.TASK_STATE_COMPLETED,
            message=new_text_message("Stock analysis complete."),
        )

    async def cancel(self, context: RequestContext, event_queue: EventQueue) -> None:
        task_updater = TaskUpdater(
            event_queue=event_queue,
            task_id=context.task_id,
            context_id=context.context_id,
        )
        await task_updater.cancel()

    # ── Private helpers ───────────────────────────────────────────────────────

    def _extract_symbol(self, text: str) -> str:
        """Best-effort ticker extraction. Falls back to AAPL."""
        known_symbols = ["AAPL", "TSLA", "GOOGL", "MSFT", "AMZN", "NVDA", "META", "NFLX", "RELIANCE", "TCS", "INFY"]
        upper = text.upper()
        for sym in known_symbols:
            if sym in upper:
                return sym
        words = text.split()
        for word in reversed(words):
            cleaned = word.strip("?.,!").upper()
            if cleaned.isalpha() and len(cleaned) >= 2:
                return cleaned
        return "AAPL"

    async def _format_with_llm(self, query: str, stock_data: dict) -> str:
        """Formats raw stock data into a 3-line analysis via LLM."""
        if stock_data.get("status") == "not_found":
            return stock_data.get("message", "Stock data not available.")

        response = await acompletion(
            model="openai/gpt-3.5-turbo",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a concise stock analyst. "
                        "Always respond in exactly 3 lines:\n"
                        "Line 1: Current price and today's change.\n"
                        "Line 2: Sentiment (Bullish / Bearish / Neutral) with one reason.\n"
                        "Line 3: Simple verdict — Good Buy, Hold, or Avoid — with one short reason."
                    ),
                },
                {
                    "role": "user",
                    "content": f"User asked: '{query}'\n\nStock data: {stock_data}\n\nFormat as a 3-line stock analysis.",
                },
            ],
            api_key=os.getenv("OPENAI_API_KEY"),
        )
        return response.choices[0].message.content.strip()
