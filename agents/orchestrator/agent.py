"""
Orchestrator Agent
──────────────────
The single entry point. Receives any user message and routes it
to the correct specialist agent (weather or stock) using ADK AgentTool.

Flow:
    User message
        └── Orchestrator LLM decides intent
                ├── weather question → delegates to weather_agent
                └── stock question   → delegates to stock_agent
"""
from google.adk.agents.llm_agent import Agent
from google.adk.tools.agent_tool import AgentTool
from google.adk.models.lite_llm import LiteLlm
from dotenv import load_dotenv
import os

from agents.weather.agent import root_agent as weather_agent
from agents.stock.agent import root_agent as stock_agent

load_dotenv()

model = LiteLlm(
    model="openai/gpt-3.5-turbo",
    api_key=os.getenv("OPENAI_API_KEY"),
)

orchestrator = Agent(
    model=model,
    name="orchestrator",
    description="Routes user requests to the correct specialist agent",
    instruction=(
        "You are a routing agent. You have two specialist agents available:\n"
        "1. weather_agent — handles all weather-related questions about cities.\n"
        "2. stock_agent   — handles all stock market questions, prices, and analysis.\n\n"
        "When the user sends a message:\n"
        "- If it is about weather, temperature, or climate of a city → delegate to weather_agent.\n"
        "- If it is about stocks, share price, buy/sell, or market analysis → delegate to stock_agent.\n"
        "- If the intent is unclear, ask the user to clarify.\n\n"
        "Always delegate. Never answer weather or stock questions yourself."
    ),
    tools=[
        AgentTool(agent=weather_agent),
        AgentTool(agent=stock_agent),
    ]
)
