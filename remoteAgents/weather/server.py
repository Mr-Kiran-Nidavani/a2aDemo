"""
Weather Agent A2A Server — port 8001

Uses Google ADK's to_a2a() to expose the ADK LlmAgent as an A2A-compliant
server. A custom AgentCard is provided so that the skill tags match exactly
what the client's discovery.py expects for routing.

Clients discover capabilities via GET /.well-known/agent-card.json
and send tasks via the JSON-RPC endpoint at POST /.
"""
from google.adk.a2a.utils.agent_to_a2a import to_a2a
from a2a.types import (
    AgentCard,
    AgentSkill,
    AgentCapabilities,
)

from remoteAgents.weather.agent import root_agent

# ── Agent Card ────────────────────────────────────────────────────────────────
# Providing a custom card so skill tags are preserved for client-side routing.
# to_a2a() serves this at GET /.well-known/agent-card.json automatically.

agent_card = AgentCard(
    name="Weather Agent",
    description=(
        "Provides current weather conditions for Indian cities. "
        "Ask about temperature, humidity, wind, and conditions for "
        "Bangalore, Mumbai, Delhi, Chennai, Hyderabad, Kolkata, or Pune."
    ),
    version="1.0.0",
    url="http://localhost:8001",
    preferred_transport="JSONRPC",
    capabilities=AgentCapabilities(streaming=False),
    default_input_modes=["text/plain"],
    default_output_modes=["text/plain"],
    skills=[
        AgentSkill(
            id="weather_lookup",
            name="Weather Lookup",
            description="Current weather conditions for a city",
            tags=[
                "weather", "temperature", "city", "climate",
                "rain", "sunny", "cloudy", "humid", "wind",
                "forecast", "hot", "cold",
            ],
            examples=[
                "What is the weather in Bangalore?",
                "How is the weather in Mumbai?",
                "Is it raining in Delhi?",
            ],
            input_modes=["text/plain"],
            output_modes=["text/plain"],
        )
    ],
)

# ── A2A App ───────────────────────────────────────────────────────────────────
# to_a2a() wires up:
#   - A2aAgentExecutor  (bridges A2A protocol ↔ ADK runner)
#   - InMemoryTaskStore + InMemoryPushNotificationConfigStore
#   - DefaultRequestHandler
#   - Starlette app with all A2A routes mounted
#   - /.well-known/agent-card.json served from our custom card

app = to_a2a(root_agent, port=8001, agent_card=agent_card)
