"""
Stock Agent A2A Server — port 8002

Exposes StockAgentExecutor as a proper A2A SDK server.
Clients discover capabilities via GET /.well-known/agent-card.json
and send tasks via the JSON-RPC endpoint.
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from a2a.server.tasks.inmemory_task_store import InMemoryTaskStore
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

from remoteAgents.stock.agent_executor import StockAgentExecutor


# ── Agent Card ────────────────────────────────────────────────────────────────
# Served at /.well-known/agent-card.json — this is how clients discover
# what this agent can do (A2A Well-Known URI discovery).

agent_card = AgentCard(
    name="Stock Agent",
    description=(
        "Provides current stock prices and brief buy/hold/avoid analysis. "
        "Supports AAPL, TSLA, GOOGL, MSFT, AMZN, NVDA, META, NFLX, "
        "RELIANCE, TCS, and INFY."
    ),
    version="1.0.0",
    capabilities=AgentCapabilities(streaming=False),
    default_input_modes=["text/plain"],
    default_output_modes=["text/plain"],
    supported_interfaces=[
        AgentInterface(
            url="http://localhost:8002",
            protocol_binding="JSONRPC",
        )
    ],
    skills=[
        AgentSkill(
            id="stock_analysis",
            name="Stock Analysis",
            description="Current stock price with a 3-line buy/hold/avoid verdict",
            tags=[
                "stock", "share", "price", "market", "invest",
                "buy", "sell", "aapl", "tsla", "nvda", "googl",
                "msft", "amzn", "meta", "nflx", "reliance", "tcs", "infy",
            ],
            examples=[
                "Give me a quick analysis of AAPL",
                "Should I buy TSLA?",
                "How is NVDA doing?",
            ],
            input_modes=["text/plain"],
            output_modes=["text/plain"],
        )
    ],
)

# ── A2A Handler & Routes ──────────────────────────────────────────────────────

handler = DefaultRequestHandler(
    agent_executor=StockAgentExecutor(),
    task_store=InMemoryTaskStore(),
    agent_card=agent_card,
)

agent_card_routes = create_agent_card_routes(agent_card)
jsonrpc_routes = create_jsonrpc_routes(handler, rpc_url="/")

# ── FastAPI App ───────────────────────────────────────────────────────────────

app = FastAPI(
    title="Stock Agent (A2A)",
    description="A2A-compliant stock agent on port 8002",
    version="1.0.0",
)

app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

add_a2a_routes_to_fastapi(app, agent_card_routes=agent_card_routes, jsonrpc_routes=jsonrpc_routes)
