"""
A2A Runner — client-side discovery and direct remote agent calls.

Uses the A2A SDK pattern:
  - A2ACardResolver  → discovers agent cards from /.well-known/agent-card.json
  - ClientFactory    → builds a Client from an AgentCard
  - ClientEvent      → (Task, UpdateEvent) pair; text extracted from Task artifacts
"""
from uuid import uuid4

import httpx

from a2a.client import A2ACardResolver, ClientConfig, ClientFactory
from a2a.client.helpers import create_text_message_object
from a2a.types import Task, TaskArtifactUpdateEvent, Message
from a2a.utils.parts import get_text_parts

from clientAgent.discovery import discover_and_match


def _build_message(user_message: str, context_id: str | None = None):
    """Builds a user Message using the SDK helper."""
    msg = create_text_message_object(content=user_message)
    msg.message_id = uuid4().hex
    msg.context_id = context_id or uuid4().hex
    return msg


def _extract_text_from_event(event) -> str:
    """
    Extracts text from a ClientEvent (Task, UpdateEvent) or a Message.

    ClientEvent = tuple[Task, TaskStatusUpdateEvent | TaskArtifactUpdateEvent | None]
    """
    if isinstance(event, tuple):
        task, update = event
        # Prefer the artifact update text if present
        if isinstance(update, TaskArtifactUpdateEvent):
            texts = get_text_parts(update.artifact.parts)
            if texts:
                return texts[-1]
        # Fall back to task artifacts
        if isinstance(task, Task) and task.artifacts:
            for artifact in reversed(task.artifacts):
                texts = get_text_parts(artifact.parts)
                if texts:
                    return texts[-1]
    elif isinstance(event, Message):
        texts = get_text_parts(event.parts)
        if texts:
            return texts[-1]
    return ""


async def run_agent(user_message: str) -> str:
    """
    Discovers remote agents by fetching their agent cards,
    matches the query to a skill, and sends the message directly
    to the matched agent via ClientFactory.

    Used by simple UI mode (trace OFF).
    """
    async with httpx.AsyncClient(timeout=60.0) as http_client:
        _, card, _ = await discover_and_match(user_message, http_client)

        if card is None:
            return (
                "I could not find a suitable agent. "
                "Try asking about weather in a city or a stock analysis."
            )

        config = ClientConfig(httpx_client=http_client, streaming=False)
        client = ClientFactory(config).create(card)
        message = _build_message(user_message)

        final_text = ""
        async for event in client.send_message(message):
            text = _extract_text_from_event(event)
            if text:
                final_text = text

    return final_text or "I could not process your request. Please try again."


async def run_agent_iter(user_message: str):
    """
    Async generator yielding raw ClientEvents from the matched agent.
    Used by tracer.py to inspect each event as it arrives.
    """
    async with httpx.AsyncClient(timeout=60.0) as http_client:
        _, card, _ = await discover_and_match(user_message, http_client)

        if card is None:
            return

        config = ClientConfig(httpx_client=http_client, streaming=False)
        client = ClientFactory(config).create(card)
        message = _build_message(user_message)

        async for event in client.send_message(message):
            yield event
