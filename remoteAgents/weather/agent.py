"""
Weather Agent — Google ADK Agent definition.

Defines the ADK LlmAgent with the get_weather function tool.
This is the core agent logic; server.py exposes it via A2A using to_a2a().
"""
import os
from dotenv import load_dotenv
from google.adk.agents import Agent
from google.adk.models.lite_llm import LiteLlm

from remoteAgents.weather.weather_tool import get_weather

load_dotenv()

root_agent = Agent(
    model=LiteLlm(
        model="openai/gpt-3.5-turbo",
        api_key=os.getenv("OPENAI_API_KEY"),
    ),
    name="weather_agent",
    description=(
        "Provides current weather conditions for Indian cities. "
        "Ask about temperature, humidity, wind, and conditions for "
        "Bangalore, Mumbai, Delhi, Chennai, Hyderabad, Kolkata, or Pune."
    ),
    instruction=(
        "You are a helpful weather assistant for Indian cities. "
        "When a user asks about the weather in a city, use the get_weather tool "
        "to fetch the data, then respond with a concise 2-3 sentence natural language "
        "summary covering temperature, condition, humidity, and wind. "
        "Supported cities: Bangalore, Mumbai, Delhi, Chennai, Hyderabad, Kolkata, Pune."
    ),
    tools=[get_weather],
)
