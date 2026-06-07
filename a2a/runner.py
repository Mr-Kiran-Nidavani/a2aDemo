"""
ADK Runner — wired to the Orchestrator agent.
All requests flow through here regardless of intent (weather or stock).
The orchestrator decides which sub-agent to call.

run_agent()            → used by the A2A server (returns final text only)
run_agent_with_trace() → used by the Streamlit UI (returns text + live trace steps)
"""
import uuid
import json

from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

from agents.orchestrator.agent import orchestrator


APP_NAME = "a2a_demo"

session_service = InMemorySessionService()

runner = Runner(
    agent=orchestrator,
    app_name=APP_NAME,
    session_service=session_service,
)


def _detect_intent(text: str) -> str:
    """Quick keyword-based intent label for trace display."""
    t = text.lower()
    if any(w in t for w in ["weather", "temperature", "rain", "sunny", "cloudy", "humid", "wind", "forecast"]):
        return "weather"
    if any(w in t for w in ["stock", "share", "price", "buy", "sell", "market", "invest", "aapl", "tsla",
                              "nvda", "googl", "msft", "amzn", "meta", "nflx", "reliance", "tcs", "infy"]):
        return "stock"
    return "unknown"


async def run_agent(user_message: str) -> str:
    """
    Plain runner used by the A2A HTTP server.
    Returns only the final text response.
    """
    session_id = str(uuid.uuid4())

    await session_service.create_session(
        app_name=APP_NAME,
        user_id="a2a_user",
        session_id=session_id,
    )

    message = types.Content(
        role="user",
        parts=[types.Part(text=user_message)]
    )

    final_response = ""

    async for event in runner.run_async(
        user_id="a2a_user",
        session_id=session_id,
        new_message=message,
    ):
        if event.is_final_response():
            if event.content and event.content.parts:
                final_response = event.content.parts[0].text
            break

    return final_response or "I could not process your request. Please try again."


async def run_agent_with_trace(user_message: str):
    """
    Trace runner used by the Streamlit UI.
    Yields trace step dicts as they happen, then yields the final response.

    Each yielded item is a dict:
        { "type": "trace", "step": int, "icon": str, "label": str, "detail": str }
    or
        { "type": "result", "text": str }
    """
    session_id = str(uuid.uuid4())
    req_id = session_id[:8]
    intent = _detect_intent(user_message)
    specialist = "weather_agent" if intent == "weather" else "stock_agent" if intent == "stock" else "unknown"

    await session_service.create_session(
        app_name=APP_NAME,
        user_id="a2a_user",
        session_id=session_id,
    )

    # ── Step 1: A2A server received the request ───────────────────────────────
    yield {
        "type": "trace",
        "step": 1,
        "icon": "🌐",
        "label": "A2A Server received request",
        "detail": json.dumps({
            "jsonrpc": "2.0",
            "id": req_id,
            "method": "message/send",
            "params": {"message": {"role": "user", "parts": [{"type": "text", "text": user_message}]}}
        }, indent=2)
    }

    # ── Step 2: Orchestrator got the message ──────────────────────────────────
    yield {
        "type": "trace",
        "step": 2,
        "icon": "🤖",
        "label": "Orchestrator received message",
        "detail": f'Reading: "{user_message}"'
    }

    # ── Step 3: Intent detected ───────────────────────────────────────────────
    intent_label = {
        "weather": "Weather question — routing to weather_agent",
        "stock":   "Stock question — routing to stock_agent",
        "unknown": "Intent unclear — asking orchestrator to decide"
    }[intent]

    yield {
        "type": "trace",
        "step": 3,
        "icon": "🧭",
        "label": f"Intent identified: {intent.upper()}",
        "detail": intent_label
    }

    # ── Step 4: Specialist agent called ──────────────────────────────────────
    if intent != "unknown":
        yield {
            "type": "trace",
            "step": 4,
            "icon": "⚡",
            "label": f"Delegating to {specialist}",
            "detail": f"Orchestrator calls AgentTool({specialist}) with: \"{user_message}\""
        }

    # ── Run ADK and trace tool calls ──────────────────────────────────────────
    message = types.Content(
        role="user",
        parts=[types.Part(text=user_message)]
    )

    tool_step = 5
    final_response = ""

    async for event in runner.run_async(
        user_id="a2a_user",
        session_id=session_id,
        new_message=message,
    ):
        # Tool call fired
        if event.content and event.content.parts:
            for part in event.content.parts:
                # Function call (tool invoked)
                if hasattr(part, "function_call") and part.function_call:
                    fc = part.function_call
                    args_str = json.dumps(dict(fc.args), indent=2) if fc.args else "{}"
                    yield {
                        "type": "trace",
                        "step": tool_step,
                        "icon": "🔧",
                        "label": f"Tool called: {fc.name}()",
                        "detail": f"Arguments:\n{args_str}"
                    }
                    tool_step += 1

                # Tool result returned
                if hasattr(part, "function_response") and part.function_response:
                    fr = part.function_response
                    resp_str = json.dumps(fr.response, indent=2) if fr.response else "{}"
                    yield {
                        "type": "trace",
                        "step": tool_step,
                        "icon": "📦",
                        "label": f"Tool response: {fr.name}()",
                        "detail": f"Returned:\n{resp_str}"
                    }
                    tool_step += 1

        # Final answer
        if event.is_final_response():
            if event.content and event.content.parts:
                final_response = event.content.parts[0].text or ""
            break

    # ── Step N: Final response wrapped in A2A format ──────────────────────────
    yield {
        "type": "trace",
        "step": tool_step,
        "icon": "📤",
        "label": "A2A Response sent back",
        "detail": json.dumps({
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {
                "status": "completed",
                "message": {
                    "role": "agent",
                    "parts": [{"type": "text", "text": final_response}]
                }
            }
        }, indent=2)
    }

    yield {
        "type": "result",
        "text": final_response or "I could not process your request. Please try again."
    }
