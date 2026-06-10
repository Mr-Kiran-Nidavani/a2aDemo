"""
A2A Tracer — live trace steps for the Streamlit UI.

Shows the true A2A client flow step by step:
  1. Discover remote agent cards via A2ACardResolver
  2. Match query skill tags on each card
  3. Send A2A request directly to the matched agent
  4. Remote agent processes and returns response

Each yielded item:
    { "type": "trace", "step": int, "icon": str, "label": str, "detail": str }
    { "type": "result", "text": str }
"""
import json
from uuid import uuid4

import httpx

from a2a.types import Message, Task, TaskArtifactUpdateEvent, TaskStatusUpdateEvent
from a2a.utils.parts import get_text_parts

from clientAgent.discovery import (
    card_name,
    card_url,
    discover_all_cards,
    discover_and_match,
    skill_id,
    skill_name,
)
from clientAgent.runner import _extract_text_from_event, run_agent_iter


def _trace(step: int, icon: str, label: str, detail: str) -> dict:
    return {"type": "trace", "step": step, "icon": icon, "label": label, "detail": detail}


async def run_agent_with_trace(user_message: str):
    req_id = uuid4().hex[:8]
    step = 1
    final_response = ""

    # ── Step 1: Discover all remote agent cards via A2ACardResolver ───────────
    async with httpx.AsyncClient(timeout=10.0) as http_client:
        discovered = await discover_all_cards(http_client)

    lines = []
    for base_url, card in discovered:
        skills_list = ", ".join(s.name for s in (card.skills or []))
        lines.append(f"{base_url}  →  {card.name}  [{skills_list}]")

    yield _trace(
        step=step, icon="📋",
        label="Remote Agent Cards discovered  (A2A Well-Known URI Discovery)",
        detail=(
            "A2ACardResolver → GET /.well-known/agent-card.json\n\n"
            + ("\n".join(lines) if lines else "No agents reachable")
        ),
    )
    step += 1

    # ── Step 2: Match skill tags against each card ────────────────────────────
    async with httpx.AsyncClient(timeout=60.0) as http_client:
        matched, remote_card, remote_url = await discover_and_match(user_message, http_client)

    if matched and remote_card:
        matched_tag = next(
            (t for t in (matched.tags or []) if t.lower() in user_message.lower()),
            "—",
        )
        skill_detail = (
            f"Query         : \"{user_message}\"\n"
            f"Matched skill : {skill_name(matched)}  (id: {skill_id(matched)})\n"
            f"Matched tag   : {matched_tag}\n"
            f"Selected agent: {card_name(remote_card)}  →  {card_url(remote_card)}"
        )
    else:
        skill_detail = (
            f"Query : \"{user_message}\"\n"
            "No skill tag matched any remote agent card."
        )

    yield _trace(
        step=step, icon="🧭",
        label=f"Skill matched: {skill_name(matched) if matched else 'None — no match'}",
        detail=skill_detail,
    )
    step += 1

    if not remote_url:
        yield {"type": "result", "text": "No suitable agent found. Try a weather or stock query."}
        return

    # ── Step 3: Confirm agent card for selected remote agent ──────────────────
    yield _trace(
        step=step, icon="🔍",
        label=f"Target Agent selected: {card_name(remote_card)}",
        detail=(
            f"Agent card URL : {remote_url}/.well-known/agent-card.json\n"
            f"Agent name     : {card_name(remote_card)}\n"
            f"Skill          : {skill_name(matched)}\n"
            f"Endpoint       : {card_url(remote_card)}"
        ),
    )
    step += 1

    # ── Step 4: A2A request sent directly to remote agent ─────────────────────
    yield _trace(
        step=step, icon="🌐",
        label=f"A2A Request sent  →  POST {card_url(remote_card)}/",
        detail=json.dumps({
            "jsonrpc": "2.0",
            "id": req_id,
            "method": "message/send",
            "params": {
                "message": {"role": "user", "parts": [{"text": user_message}]}
            },
        }, indent=2),
    )
    step += 1

    # ── Step 5: Collect events ────────────────────────────────────────────────
    async for event in run_agent_iter(user_message):
        # Check for WORKING status update to show live processing step
        try:
            if isinstance(event, tuple):
                _, update = event
                if isinstance(update, TaskStatusUpdateEvent):
                    state = str(update.status.state)
                    if "working" in state.lower():
                        yield _trace(
                            step=step, icon="🔧",
                            label="Remote agent processing",
                            detail=f"Task state: {state}\nCalling tool + formatting response with LLM...",
                        )
                        step += 1
        except Exception:
            pass

        # Collect final text from the event
        text = _extract_text_from_event(event)
        if text:
            final_response = text

    # ── Step 6: Response returned ─────────────────────────────────────────────
    yield _trace(
        step=step, icon="📤",
        label="A2A Response returned",
        detail=json.dumps({
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {
                "status": "completed",
                "artifacts": [{"parts": [{"text": final_response}]}]
            },
        }, indent=2),
    )

    yield {
        "type": "result",
        "text": final_response or "I could not process your request. Please try again.",
    }
