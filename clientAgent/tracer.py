"""
A2A Tracer — live trace steps for the Streamlit UI.

Responsible for:
- Reading the agent card for discovery info
- Matching the query to a skill via discovery.py
- Yielding formatted trace step dicts as the request flows through the system
- Capturing ADK events (tool calls, responses) from runner.py

Nothing here touches HTTP or ADK session logic directly.
That stays in runner.py and server.py.

Each yielded item is one of:
    { "type": "trace", "step": int, "icon": str, "label": str, "detail": str }
    { "type": "result", "text": str }
"""
import json
import uuid

from clientAgent.agent_card import AGENT_CARD
from clientAgent.discovery import match_skill, skill_to_agent
from clientAgent.runner import make_session, drop_session, run_agent_iter


def _trace(step: int, icon: str, label: str, detail: str) -> dict:
    """Shorthand to build a trace item dict."""
    return {"type": "trace", "step": step, "icon": icon, "label": label, "detail": detail}


async def run_agent_with_trace(user_message: str):
    """
    Yields live trace steps as the message flows through the A2A system,
    then yields the final result.

    Trace steps:
      1. Agent card read       — A2A discovery
      2. Skill matched         — card-based routing awareness
      3. A2A request sent      — JSON-RPC payload
      4. Orchestrator thinking — LLM decides which agent to call
      5+ Tool calls / responses — captured from ADK events
      N. A2A response returned — final JSON-RPC response
    """
    req_id       = str(uuid.uuid4())[:8]
    session_id   = await create_session()
    matched      = match_skill(user_message, AGENT_CARD)
    specialist   = skill_to_agent(matched)

    # ── Step 1: Agent card read (A2A Discovery) ───────────────────────────────
    yield _trace(
        step=1, icon="📋",
        label="Agent Card read  (A2A Discovery)",
        detail=(
            f"GET /.well-known/agent.json\n"
            f"Agent : {AGENT_CARD['name']}\n"
            f"Skills: {', '.join(s['name'] for s in AGENT_CARD['skills'])}"
        )
    )

    # ── Step 2: Skill matched against card tags ───────────────────────────────
    if matched:
        matched_tag = next(
            (t for t in matched["tags"] if t.lower() in user_message.lower()), "—"
        )
        detail = (
            f"Query         : \"{user_message}\"\n"
            f"Matched skill : {matched['name']}  (id: {matched['id']})\n"
            f"Matched tag   : {matched_tag}\n"
            f"Routes to     : {specialist}"
        )
    else:
        detail = (
            f"Query : \"{user_message}\"\n"
            f"No skill tag matched — orchestrator LLM will decide"
        )

    yield _trace(
        step=2, icon="🧭",
        label=f"Skill matched: {matched['name'] if matched else 'None — LLM decides'}",
        detail=detail
    )

    # ── Step 3: A2A request sent ──────────────────────────────────────────────
    yield _trace(
        step=3, icon="🌐",
        label="A2A Request sent  POST /a2a",
        detail=json.dumps({
            "jsonrpc": "2.0", "id": req_id, "method": "message/send",
            "params": {"message": {"role": "user", "parts": [{"type": "text", "text": user_message}]}}
        }, indent=2)
    )

    # ── Step 4: Orchestrator thinking ─────────────────────────────────────────
    yield _trace(
        step=4, icon="🤖",
        label="Orchestrator received message",
        detail=(
            f"Message         : \"{user_message}\"\n"
            f"Available agents: weather_agent, stock_agent\n"
            f"LLM deciding which agent to delegate to..."
        )
    )

    # ── Steps 5+: Live ADK events ─────────────────────────────────────────────
    step = 5
    final_response = ""
    delegated_to = None

    async for event in run_agent_iter(user_message, session_id):
        if event.content and event.content.parts:
            for part in event.content.parts:

                # Function call — either orchestrator delegating, or specialist using a tool
                if hasattr(part, "function_call") and part.function_call:
                    fc = part.function_call
                    args_str = json.dumps(dict(fc.args), indent=2) if fc.args else "{}"

                    if delegated_to is None and fc.name in ("weather_agent", "stock_agent"):
                        # Orchestrator delegating to a specialist
                        delegated_to = fc.name
                        yield _trace(
                            step=step, icon="⚡",
                            label=f"Orchestrator delegated to: {fc.name}",
                            detail=(
                                f"LLM confirmed — matches card skill: "
                                f"{matched['name'] if matched else 'N/A'}\n"
                                f"Calling AgentTool({fc.name}) with:\n{args_str}"
                            )
                        )
                    else:
                        # Specialist calling its own tool (get_weather / get_stock)
                        yield _trace(
                            step=step, icon="🔧",
                            label=f"Tool called: {fc.name}()",
                            detail=f"Arguments:\n{args_str}"
                        )
                    step += 1

                # Function response — tool returned data
                if hasattr(part, "function_response") and part.function_response:
                    fr = part.function_response
                    resp_str = json.dumps(fr.response, indent=2) if fr.response else "{}"
                    yield _trace(
                        step=step, icon="📦",
                        label=f"Tool response: {fr.name}()",
                        detail=f"Returned:\n{resp_str}"
                    )
                    step += 1

        if event.is_final_response():
            if event.content and event.content.parts:
                final_response = event.content.parts[0].text or ""
            break

    # ── Step N: A2A response returned ─────────────────────────────────────────
    yield _trace(
        step=step, icon="📤",
        label="A2A Response returned",
        detail=json.dumps({
            "jsonrpc": "2.0", "id": req_id,
            "result": {
                "status": "completed",
                "message": {"role": "agent", "parts": [{"type": "text", "text": final_response}]}
            }
        }, indent=2)
    )

    yield {"type": "result", "text": final_response or "I could not process your request. Please try again."}
