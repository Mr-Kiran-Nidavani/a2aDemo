"""
A2A Runner — client-side discovery and direct remote agent calls.

Uses the official A2A SDK pattern:
  - A2ACardResolver     → discovers agent cards from /.well-known/agent-card.json
  - create_client       → builds a Client from an AgentCard
  - get_stream_response_text → extracts text from StreamResponse
"""
from uuid import uuid4

import httpx

from a2a.client import ClientConfig, create_client
from a2a.helpers import get_stream_response_text, new_text_message
from a2a.types import (
    Role,
    SendMessageConfiguration,
    SendMessageRequest,
)

from clientAgent.discovery import discover_and_match


def _build_request(user_message: str, context_id: str | None = None) -> SendMessageRequest:
    """Builds a standard A2A SendMessageRequest using new_text_message helper (official SDK pattern)."""
    from uuid import uuid4
    msg = new_text_message(user_message, role=Role.ROLE_USER)
    msg.message_id = uuid4().hex
    msg.context_id = context_id or uuid4().hex
    return SendMessageRequest(
        message=msg,
        configuration=SendMessageConfiguration(),
    )


async def run_agent(user_message: str) -> str:
    """
    Discovers remote agents by fetching their agent cards,
    matches the query to a skill, and sends the message directly
    to the matched agent via create_client.

    Used by simple UI mode (trace OFF).
    """
    async with httpx.AsyncClient(timeout=60.0) as http_client:
        _, card, base_url = await discover_and_match(user_message, http_client)

        if card is None:
            return (
                "I could not find a suitable agent. "
                "Try asking about weather in a city or a stock analysis."
            )

        config = ClientConfig(httpx_client=http_client, streaming=False)
        client = await create_client(agent=card, client_config=config)
        request = _build_request(user_message)

        final_text = ""
        async for response in client.send_message(request):
            text = get_stream_response_text(response)
            if text:
                final_text = text

    return final_text or "I could not process your request. Please try again."


async def run_agent_iter(user_message: str):
    """
    Async generator yielding raw StreamResponse objects from the matched agent.
    Used by tracer.py to inspect each event as it arrives.
    """
    async with httpx.AsyncClient(timeout=60.0) as http_client:
        _, card, _ = await discover_and_match(user_message, http_client)

        if card is None:
            return

        config = ClientConfig(httpx_client=http_client, streaming=False)
        client = await create_client(agent=card, client_config=config)
        request = _build_request(user_message)

        async for response in client.send_message(request):
            yield response
