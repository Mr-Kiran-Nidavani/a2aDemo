"""
A2A Tracer — live trace steps for the Streamlit UI.

Shows the true A2A client flow (no orchestrator):
  1. Discover remote agent cards
  2. Match query to a skill
  3. Send A2A request directly to the matched agent
  4. Remote agent processes and returns response

Each yielded item is one of:
    { "type": "trace", "step": int, "icon": str, "label": str, "detail": str }
    { "type": "result", "text": str }
"""
import json
from uuid import uuid4

import httpx

from clientAgent.discovery import (
    REMOTE_AGENT_URLS,
    card_name,
    discover_all_cards,
    discover_and_match,
    match_skill,
    skill_id,
    skill_name,
)
from clientAgent.runner import run_agent_iter, _extract_text


def _trace(step: int, icon: str, label: str, detail: str) -> dict:
    return {"type": "trace", "step": step, "icon": icon, "label": label, "detail": detail}


async def run_agent_with_trace(user_message: str):
    req_id = uuid4().hex[:8]
    step = 1
    final_response = ""
    remote_url = None
    matched = None

    # ── Step 1: Discover all remote agent cards ───────────────────────────────
    async with httpx.AsyncClient(timeout=10.0) as http_client:
        discovered = await discover_all_cards(http_client)

    lines = []
    for base_url, card in discovered:
        skill_names = ", ".join(s.name for s in (card.skills or []))
        lines.append(f"{base_url}  →  {card.name}  [{skill_names}]")

    yield _trace(
        step=step,
        icon="📋",
        label="Remote Agent Cards discovered  (A2A Discovery)",
        detail=(
            "Client fetches /.well-known/agent-card.json from each known agent:\n"
            + ("\n".join(lines) if lines else "No agents reachable")
        ),
    )
    step += 1

    # ── Step 2: Match skill across discovered cards ───────────────────────────
    async with httpx.AsyncClient(timeout=60.0) as http_client:
        matched, remote_card, remote_url = await discover_and_match(
            user_message, http_client
        )

    if matched and remote_url:
        matched_tag = next(
            (
                t
                for t in (
                    matched.get("tags", [])
                    if isinstance(matched, dict)
                    else (matched.tags or [])
                )
                if t.lower() in user_message.lower()
            ),
            "—",
        )
        skill_detail = (
            f"Query         : \"{user_message}\"\n"
            f"Matched skill : {skill_name(matched)}  (id: {skill_id(matched)})\n"
            f"Matched tag   : {matched_tag}\n"
            f"Selected agent: {card_name(remote_card)}  ({remote_url})"
        )
    else:
        skill_detail = (
            f"Query : \"{user_message}\"\n"
            "No skill tag matched any remote agent card."
        )

    yield _trace(
        step=step,
        icon="🧭",
        label=f"Skill matched: {skill_name(matched) if matched else 'None'}",
        detail=skill_detail,
    )
    step += 1

    if not remote_url:
        yield {
            "type": "result",
            "text": (
                "I could not find a suitable agent for your request. "
                "Try asking about weather in a city or a stock analysis."
            ),
        }
        return

    # ── Step 3: Confirm selected agent card ───────────────────────────────────
    # Uses A2ACardResolver — the official SDK way to do agent discovery
    try:
        async with httpx.AsyncClient(timeout=10.0) as http_client:
            from a2a.client import A2ACardResolver
            resolver = A2ACardResolver(httpx_client=http_client, base_url=remote_url)
            r_card = await resolver.get_agent_card()
            remote_name = r_card.name
    except Exception:
        remote_name = "Remote Agent (unreachable)"

    yield _trace(
        step=step,
        icon="🔍",
        label=f"Target Agent Card  ({remote_url})",
        detail=(
            f"GET {remote_url}/.well-known/agent-card.json\n"
            f"Agent : {remote_name}\n"
            f"Skill : {skill_name(matched)}"
        ),
    )
    step += 1

    # ── Step 4: A2A request sent directly to remote agent ─────────────────────
    yield _trace(
        step=step,
        icon="🌐",
        label=f"A2A Request sent  POST {remote_url}/",
        detail=json.dumps(
            {
                "jsonrpc": "2.0",
                "id": req_id,
                "method": "SendMessage",
                "params": {
                    "message": {
                        "role": "user",
                        "parts": [{"text": user_message}],
                    }
                },
            },
            indent=2,
        ),
    )
    step += 1

    # ── Step 5: Collect StreamResponse events from remote agent ───────────────
    async for response in run_agent_iter(user_message):
        text = _extract_text(response)
        if text:
            final_response = text

        try:
            if hasattr(response, "task") and response.task:
                state = str(response.task.status.state)
                if "working" in state.lower():
                    yield _trace(
                        step=step,
                        icon="🔧",
                        label="Remote agent processing",
                        detail=(
                            f"Task state: {state}\n"
                            f"Agent at {remote_url} calling tool and formatting response..."
                        ),
                    )
                    step += 1
        except Exception:
            pass

    # ── Step 6: A2A response returned ─────────────────────────────────────────
    yield _trace(
        step=step,
        icon="📤",
        label="A2A Response returned",
        detail=json.dumps(
            {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {
                    "status": "completed",
                    "message": {
                        "role": "agent",
                        "parts": [{"text": final_response}],
                    },
                },
            },
            indent=2,
        ),
    )

    yield {
        "type": "result",
        "text": final_response or "I could not process your request. Please try again.",
    }
