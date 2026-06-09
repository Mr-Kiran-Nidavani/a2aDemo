"""
A2A Runner — client-side discovery and direct remote agent calls.

Responsible for:
  1. Discovering remote agent cards (ports 8001, 8002)
  2. Matching the user query to a skill via discovery.py
  3. Sending a SendMessageRequest directly to the matched agent
  4. Returning the final text response

No orchestrator — the client performs A2A discovery and routing.
For the traced version used by the Streamlit UI, see tracer.py.
"""
from uuid import uuid4

import httpx

from a2a.client.client_factory import ClientConfig, ClientFactory
from a2a.types import (
    Message,
    Part,
    Role,
    SendMessageConfiguration,
    SendMessageRequest,
    StreamResponse,
)

from clientAgent.discovery import discover_and_match


def _build_request(user_message: str, context_id: str | None = None) -> SendMessageRequest:
    return SendMessageRequest(
        message=Message(
            message_id=uuid4().hex,
            context_id=context_id or uuid4().hex,
            role=Role.ROLE_USER,
            parts=[Part(text=user_message)],
        ),
        configuration=SendMessageConfiguration(),
    )


async def run_agent(user_message: str) -> str:
    """
    Discovers remote agents, matches skills, and sends the message directly
    to the appropriate specialist agent via the A2A SDK Client.
    """
    async with httpx.AsyncClient(timeout=60.0) as http_client:
        matched_skill, card, base_url = await discover_and_match(
            user_message, http_client
        )

        if card is None or base_url is None:
            return (
                "I could not find a suitable agent for your request. "
                "Try asking about weather in a city or a stock analysis."
            )

        factory = ClientFactory(ClientConfig(httpx_client=http_client, streaming=False))
        client = factory.create(card)
        request = _build_request(user_message)

        final_text = ""
        async for response in client.send_message(request):
            text = _extract_text(response)
            if text:
                final_text = text

    return final_text or "I could not process your request. Please try again."


async def run_agent_iter(user_message: str):
    """
    Async generator that yields raw StreamResponse objects from the matched
    remote agent. Used by tracer.py to inspect each event as it arrives.
    """
    async with httpx.AsyncClient(timeout=60.0) as http_client:
        matched_skill, card, base_url = await discover_and_match(
            user_message, http_client
        )

        if card is None:
            return

        factory = ClientFactory(ClientConfig(httpx_client=http_client, streaming=False))
        client = factory.create(card)
        request = _build_request(user_message)

        async for response in client.send_message(request):
            yield response


def _extract_text(response: StreamResponse) -> str:
    """Extracts text content from a StreamResponse (A2A SDK protobuf)."""
    try:
        if hasattr(response, "task") and response.task:
            task = response.task
            if task.status and task.status.message and task.status.message.parts:
                return task.status.message.parts[0].text or ""

        if hasattr(response, "result"):
            result = response.result
            if hasattr(result, "status") and hasattr(result.status, "message"):
                msg = result.status.message
                if msg and msg.parts:
                    return msg.parts[0].text or ""
            if hasattr(result, "artifact"):
                artifact = result.artifact
                if artifact and artifact.parts:
                    return artifact.parts[0].text or ""

        if hasattr(response, "message"):
            msg = response.message
            if msg and msg.parts:
                return msg.parts[0].text or ""
    except Exception:
        pass
    return ""
