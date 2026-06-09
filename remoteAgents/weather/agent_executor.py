"""
WeatherAgentExecutor — A2A SDK AgentExecutor for the Weather agent.

Follows the official A2A SDK pattern (from the docs):
  1. Create or retrieve task, enqueue it
  2. Update status → WORKING
  3. Execute business logic (tool call + LLM format)
  4. Add result as an artifact
  5. Update status → COMPLETED
"""
import os

from dotenv import load_dotenv
from litellm import acompletion

from a2a.server.agent_execution.agent_executor import AgentExecutor
from a2a.server.agent_execution.context import RequestContext
from a2a.server.events.event_queue import EventQueue
from a2a.server.tasks.task_updater import TaskUpdater
from a2a.types import TaskState
from a2a.helpers import (
    get_message_text,
    new_task_from_user_message,
    new_text_message,
    new_text_part,
)

from remoteAgents.weather.weather_tool import get_weather

load_dotenv()


class WeatherAgentExecutor(AgentExecutor):
    """Handles weather queries following the official A2A executor pattern."""

    async def execute(self, context: RequestContext, event_queue: EventQueue) -> None:
        # Step 1: Create or retrieve task and enqueue it
        if context.current_task:
            task = context.current_task
        else:
            task = new_task_from_user_message(context.message)
            await event_queue.enqueue_event(task)

        task_updater = TaskUpdater(
            event_queue=event_queue,
            task_id=task.id,
            context_id=task.context_id,
        )

        # Step 2: Signal working
        await task_updater.update_status(
            state=TaskState.TASK_STATE_WORKING,
            message=new_text_message("Looking up weather data..."),
        )

        # Step 3: Extract city from query and call the weather tool
        user_text = get_message_text(context.message) or ""
        city = self._extract_city(user_text)
        weather_data = get_weather(city)

        # Step 4: Format with LLM and add as artifact
        formatted = await self._format_with_llm(user_text, weather_data)
        await task_updater.add_artifact(
            parts=[new_text_part(text=formatted, media_type="text/plain")],
            name="weather_result",
        )

        # Step 5: Mark completed
        await task_updater.update_status(
            state=TaskState.TASK_STATE_COMPLETED,
            message=new_text_message("Weather lookup complete."),
        )

    async def cancel(self, context: RequestContext, event_queue: EventQueue) -> None:
        task_updater = TaskUpdater(
            event_queue=event_queue,
            task_id=context.task_id,
            context_id=context.context_id,
        )
        await task_updater.cancel()

    # ── Private helpers ───────────────────────────────────────────────────────

    def _extract_city(self, text: str) -> str:
        """Best-effort city extraction. Falls back to Bangalore."""
        known_cities = ["bangalore", "mumbai", "delhi", "chennai", "hyderabad", "kolkata", "pune"]
        lower = text.lower()
        for city in known_cities:
            if city in lower:
                return city.title()
        words = lower.split()
        for i, word in enumerate(words):
            if word == "in" and i + 1 < len(words):
                return words[i + 1].title()
        return "Bangalore"

    async def _format_with_llm(self, query: str, weather_data: dict) -> str:
        """Formats raw weather data into natural language via LLM."""
        if weather_data.get("status") == "not_found":
            return weather_data.get("message", "Weather data not available.")

        response = await acompletion(
            model="openai/gpt-3.5-turbo",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a helpful weather assistant. "
                        "Given raw weather data, write a concise 2-3 sentence natural language summary."
                    ),
                },
                {
                    "role": "user",
                    "content": f"User asked: '{query}'\n\nWeather data: {weather_data}\n\nFormat as a natural language weather report.",
                },
            ],
            api_key=os.getenv("OPENAI_API_KEY"),
        )
        return response.choices[0].message.content.strip()
