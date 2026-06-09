"""
Weather Agent A2A Server — port 8001

Exposes WeatherAgentExecutor as a proper A2A SDK server.
Clients discover capabilities via GET /.well-known/agent-card.json
and send tasks via the JSON-RPC endpoint.
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from a2a.server.tasks.inmemory_task_store import InMemoryTaskStore
from a2a.server.events.in_memory_queue_manager import InMemoryQueueManager
from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.routes import (
    create_agent_card_routes,
    create_jsonrpc_routes,
    add_a2a_routes_to_fastapi,
)
from a2a.types import (
    AgentCard,
    AgentSkill,
    AgentCapabilities,
    AgentInterface,
)

from remoteAgents.weather.agent_executor import WeatherAgentExecutor


# ── Agent Card ────────────────────────────────────────────────────────────────
# Each remote agent declares its identity and skills here.
# This is the A2A "registration" — served at /.well-known/agent-card.json
# so any client can discover what this agent can do.

agent_card = AgentCard(
    name="Weather Agent",
    description=(
        "Provides current weather conditions for Indian cities. "
        "Ask about temperature, humidity, wind, and conditions for "
        "Bangalore, Mumbai, Delhi, Chennai, Hyderabad, Kolkata, or Pune."
    ),
    version="1.0.0",
    capabilities=AgentCapabilities(streaming=False),
    default_input_modes=["text/plain"],
    default_output_modes=["text/plain"],
    supported_interfaces=[
        AgentInterface(
            url="http://localhost:8001",
            protocol_binding="JSONRPC",
        )
    ],
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

# ── A2A Handler & Routes ──────────────────────────────────────────────────────
# DefaultRequestHandler wires the AgentExecutor into the A2A request lifecycle.
# It handles task creation, status updates, and event routing.

handler = DefaultRequestHandler(
    agent_executor=WeatherAgentExecutor(),
    task_store=InMemoryTaskStore(),
    agent_card=agent_card,
)

# create_agent_card_routes → exposes GET /.well-known/agent-card.json
# create_jsonrpc_routes    → exposes POST / for A2A JSON-RPC calls
agent_card_routes = create_agent_card_routes(agent_card)
jsonrpc_routes = create_jsonrpc_routes(handler, rpc_url="/")

# ── FastAPI App ───────────────────────────────────────────────────────────────

app = FastAPI(
    title="Weather Agent (A2A)",
    description="A2A-compliant weather agent on port 8001",
    version="1.0.0",
)

app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

add_a2a_routes_to_fastapi(app, agent_card_routes=agent_card_routes, jsonrpc_routes=jsonrpc_routes)
