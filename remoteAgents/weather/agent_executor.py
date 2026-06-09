"""
WeatherAgentExecutor — A2A SDK AgentExecutor for the Weather agent.

Receives a task via RequestContext, calls get_weather(), formats with LLM,
publishes the result via TaskUpdater, and marks the task complete.
"""
import os
from uuid import uuid4

from dotenv import load_dotenv
from litellm import acompletion

from a2a.server.agent_execution.agent_executor import AgentExecutor
from a2a.server.agent_execution.context import RequestContext
from a2a.server.events.event_queue import EventQueue
from a2a.server.tasks.task_updater import TaskUpdater
from a2a.types import Part, TaskState

from remoteAgents.weather.weather_tool import get_weather

load_dotenv()


class WeatherAgentExecutor(AgentExecutor):
    """Handles weather queries end-to-end using the A2A TaskUpdater pattern."""

    async def execute(self, context: RequestContext, event_queue: EventQueue) -> None:
        task_updater = TaskUpdater(
            event_queue=event_queue,
            task_id=context.task_id,
            context_id=context.context_id,
        )

        # Mark task as working
        await task_updater.update_status(TaskState.TASK_STATE_WORKING)

        # Extract user text
        try:
            user_text = context.message.parts[0].text or ""
        except (AttributeError, IndexError):
            user_text = ""

        # Call the mock weather tool — extract city from text heuristically
        city = self._extract_city(user_text)
        weather_data = get_weather(city)

        # Format response using LLM
        formatted = await self._format_with_llm(user_text, weather_data)

        # Publish result and complete
        result_message = task_updater.new_agent_message(parts=[Part(text=formatted)])
        await task_updater.complete(message=result_message)

    async def cancel(self, context: RequestContext, event_queue: EventQueue) -> None:
        task_updater = TaskUpdater(
            event_queue=event_queue,
            task_id=context.task_id,
            context_id=context.context_id,
        )
        await task_updater.cancel()

    # ── Private helpers ───────────────────────────────────────────────────────

    def _extract_city(self, text: str) -> str:
        """
        Best-effort city extraction from natural language.
        Falls back to 'Bangalore' if nothing recognised.
        """
        known_cities = [
            "bangalore", "mumbai", "delhi", "chennai",
            "hyderabad", "kolkata", "pune",
        ]
        lower = text.lower()
        for city in known_cities:
            if city in lower:
                return city.title()
        # Try 'in <word>' pattern
        words = lower.split()
        for i, word in enumerate(words):
            if word == "in" and i + 1 < len(words):
                return words[i + 1].title()
        return "Bangalore"

    async def _format_with_llm(self, query: str, weather_data: dict) -> str:
        """Sends weather data to the LLM and returns a natural-language response."""
        if weather_data.get("status") == "not_found":
            return weather_data.get("message", "Weather data not available.")

        system_prompt = (
            "You are a helpful weather assistant. "
            "Given raw weather data, write a concise 2-3 sentence natural language summary. "
            "Be friendly and informative."
        )
        user_prompt = (
            f"User asked: '{query}'\n\n"
            f"Weather data: {weather_data}\n\n"
            "Please format this into a natural language weather report."
        )

        response = await acompletion(
            model="openai/gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            api_key=os.getenv("OPENAI_API_KEY"),
        )
        return response.choices[0].message.content.strip()
