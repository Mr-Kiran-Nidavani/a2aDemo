"""
Stock Agent A2A Server — port 8002

Exposes StockAgentExecutor as an A2A-compliant server using the new
A2AFastAPIApplication API (a2a-sdk >= 1.1).

Clients discover capabilities via GET /.well-known/agent-card.json
and send tasks via the JSON-RPC endpoint at POST /.
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from a2a.server.apps import A2AFastAPIApplication
from a2a.server.tasks.inmemory_task_store import InMemoryTaskStore
from a2a.server.request_handlers import DefaultRequestHandler
from a2a.types import (
    AgentCard,
    AgentSkill,
    AgentCapabilities,
)

from remoteAgents.stock.agent_executor import StockAgentExecutor


# ── Agent Card ────────────────────────────────────────────────────────────────

agent_card = AgentCard(
    name="Stock Agent",
    description=(
        "Provides current stock prices and brief buy/hold/avoid analysis. "
        "Supports AAPL, TSLA, GOOGL, MSFT, AMZN, NVDA, META, NFLX, "
        "RELIANCE, TCS, and INFY."
    ),
    version="1.0.0",
    url="http://localhost:8002",
    preferred_transport="JSONRPC",
    capabilities=AgentCapabilities(streaming=False),
    default_input_modes=["text/plain"],
    default_output_modes=["text/plain"],
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

# ── A2A Handler ───────────────────────────────────────────────────────────────

handler = DefaultRequestHandler(
    agent_executor=StockAgentExecutor(),
    task_store=InMemoryTaskStore(),
)

# ── FastAPI App ───────────────────────────────────────────────────────────────

app = FastAPI(
    title="Stock Agent (A2A)",
    description="A2A-compliant stock agent on port 8002",
    version="1.0.0",
)

app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

# Mount A2A routes: POST / (JSON-RPC) + GET /.well-known/agent-card.json
A2AFastAPIApplication(agent_card=agent_card, http_handler=handler).add_routes_to_app(app)
