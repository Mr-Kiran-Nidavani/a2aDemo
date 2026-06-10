"""
StockAgentExecutor — LangChain agent wrapped in the A2A protocol.

Uses ChatOpenAI via LiteLLM proxy (same model as the Weather ADK agent)
so both agents use a consistent LLM backend.
"""
import os
from dotenv import load_dotenv

from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage
from langchain_core.tools import tool

from a2a.server.agent_execution.agent_executor import AgentExecutor
from a2a.server.agent_execution.context import RequestContext
from a2a.server.events.event_queue import EventQueue
from a2a.server.tasks.task_updater import TaskUpdater
from a2a.types import Part, TaskState, TextPart
from a2a.utils import get_message_text, new_task
from a2a.utils.message import new_agent_text_message

from remoteAgents.stock.stock_tool import get_stock as _get_stock_data

load_dotenv()


# ── LangChain tool ────────────────────────────────────────────────────────────

@tool
def get_stock(symbol: str) -> str:
    """
    Returns stock price, change, sentiment and note for a ticker.
    Supported: AAPL, TSLA, GOOGL, MSFT, AMZN, NVDA, META, NFLX, RELIANCE, TCS, INFY.
    """
    d = _get_stock_data(symbol)
    if d.get("status") == "not_found":
        return d["message"]
    return (
        f"{d['symbol']}: ${d['price']} {d['direction']}{abs(d['change'])} "
        f"({d['change_pct']:+.2f}%) | {d['sentiment']} | {d['note']}"
    )


# ── LangChain model — same backend as the Weather ADK agent ──────────────────

_llm_with_tools = ChatOpenAI(
    model="gpt-3.5-turbo",
    api_key=os.getenv("OPENAI_API_KEY"),
    temperature=0.2,
).bind_tools([get_stock])

# Plain LLM without tools — used for the final formatting step
_llm = ChatOpenAI(
    model="gpt-3.5-turbo",
    api_key=os.getenv("OPENAI_API_KEY"),
    temperature=0.2,
)


# ── A2A bridge ────────────────────────────────────────────────────────────────

class StockAgentExecutor(AgentExecutor):
    """Thin A2A wrapper around the LangChain + GPT-3.5 stock agent."""

    async def execute(self, context: RequestContext, event_queue: EventQueue) -> None:
        task = context.current_task or new_task(context.message)
        if not context.current_task:
            await event_queue.enqueue_event(task)

        updater = TaskUpdater(event_queue=event_queue, task_id=task.id, context_id=task.context_id)
        await updater.update_status(TaskState.working, new_agent_text_message("Fetching stock data..."))

        user_text = get_message_text(context.message) if context.message else ""

        try:
            # Step 1 — ask the model which tool to call
            response = await _llm_with_tools.ainvoke([HumanMessage(content=user_text)])

            # Step 2 — if the model requested a tool, call it; then format with plain LLM
            if response.tool_calls:
                tool_result = get_stock.invoke(response.tool_calls[0]["args"])

                final = await _llm.ainvoke([
                    HumanMessage(content=(
                        f"User asked: {user_text}\n\n"
                        f"Stock data: {tool_result}\n\n"
                        "Respond in exactly 3 lines:\n"
                        "Line 1: Current price and today's change.\n"
                        "Line 2: Sentiment (Bullish/Bearish/Neutral) with one reason.\n"
                        "Line 3: Verdict — Good Buy, Hold, or Avoid — with one short reason."
                    ))
                ])
                result_text = final.content or tool_result  # fallback to raw data if LLM returns empty
            else:
                result_text = response.content or "No analysis available."
        except Exception as e:
            result_text = f"Stock analysis failed: {e}"

        await updater.add_artifact(parts=[Part(root=TextPart(text=result_text))], name="stock_result")
        await updater.update_status(TaskState.completed, new_agent_text_message("Done."))

    async def cancel(self, context: RequestContext, event_queue: EventQueue) -> None:
        updater = TaskUpdater(event_queue=event_queue, task_id=context.task_id, context_id=context.context_id)
        await updater.cancel()
