import uuid

from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

from agents.weather.agent import root_agent


APP_NAME = "weather_app"

session_service = InMemorySessionService()

runner = Runner(
    agent=root_agent,
    app_name=APP_NAME,
    session_service=session_service,
)


async def run_agent(user_message: str) -> str:
    session_id = str(uuid.uuid4())

    await session_service.create_session(
        app_name=APP_NAME,
        user_id="a2a_user",
        session_id=session_id,
    )

    message = types.Content(
        role="user",
        parts=[
            types.Part(text=user_message)
        ]
    )

    final_response = ""

    async for event in runner.run_async(
        user_id="a2a_user",
        session_id=session_id,
        new_message=message,
    ):
        if event.content and event.content.parts:
            final_response = event.content.parts[0].text

    return final_response