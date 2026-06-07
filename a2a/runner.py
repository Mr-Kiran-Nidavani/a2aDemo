"""
ADK Runner — pure execution logic only.

Responsible for:
- Creating an ADK session
- Running the orchestrator agent
- Returning the final text response

No trace, no formatting, no UI concerns here.
For the traced version used by the Streamlit UI, see a2a/tracer.py
"""
import uuid

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


async def create_session() -> str:
    """Creates a fresh ADK session and returns the session_id."""
    session_id = str(uuid.uuid4())
    await session_service.create_session(
        app_name=APP_NAME,
        user_id="a2a_user",
        session_id=session_id,
    )
    return session_id


async def run_agent(user_message: str) -> str:
    """
    Runs the orchestrator agent with the given message.
    Returns the final text response.
    Used by the A2A HTTP server.
    """
    session_id = await create_session()

    message = types.Content(
        role="user",
        parts=[types.Part(text=user_message)]
    )

    async for event in runner.run_async(
        user_id="a2a_user",
        session_id=session_id,
        new_message=message,
    ):
        if event.is_final_response():
            if event.content and event.content.parts:
                return event.content.parts[0].text

    return "I could not process your request. Please try again."


async def run_agent_iter(user_message: str, session_id: str):
    """
    Raw event iterator over the ADK run loop.
    Used by tracer.py to inspect each event as it happens.
    Yields raw ADK events — no formatting done here.
    """
    message = types.Content(
        role="user",
        parts=[types.Part(text=user_message)]
    )

    async for event in runner.run_async(
        user_id="a2a_user",
        session_id=session_id,
        new_message=message,
    ):
        yield event
