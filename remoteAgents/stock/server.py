"""
Stock Agent A2A Server — port 8002

Exposes StockAgentExecutor as a proper A2A SDK server.
Clients discover capabilities via GET /.well-known/agent-card.json
and send tasks via the JSON-RPC endpoint.
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from a2a.server.tasks.inmemory_task_store import InMemoryTaskStore
from a2a.server.events.in_memory_queue_manager import InMemoryQueueManager
from a2a.server.request_handlers.default_request_handler import LegacyRequestHandler
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

agent_card = AgentCard(
    name="Stock Agent",
    description=(
        "Provides current stock prices and brief buy/hold/avoid analysis. "
        "Supports AAPL, TSLA, GOOGL, MSFT, AMZN, NVDA, META, NFLX, "
        "RELIANCE, TCS, and INFY."
    ),
    version="1.0.0",
    capabilities=AgentCapabilities(
        streaming=False,
        push_notifications=False,
    ),
    default_input_modes=["text"],
    default_output_modes=["text"],
    supported_interfaces=[
        AgentInterface(
            url="http://localhost:8002",
            protocol_binding="JSONRPC",
            protocol_version="1.0",
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
            input_modes=["text"],
            output_modes=["text"],
        )
    ],
)

# ── A2A Handler & Routes ──────────────────────────────────────────────────────

task_store = InMemoryTaskStore()
queue_manager = InMemoryQueueManager()
executor = StockAgentExecutor()

handler = LegacyRequestHandler(
    agent_executor=executor,
    task_store=task_store,
    agent_card=agent_card,
    queue_manager=queue_manager,
)

agent_card_routes = create_agent_card_routes(agent_card)
jsonrpc_routes = create_jsonrpc_routes(handler, rpc_url="/")

# ── FastAPI App ───────────────────────────────────────────────────────────────

app = FastAPI(
    title="Stock Agent (A2A)",
    description="A2A-compliant stock agent on port 8002",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

add_a2a_routes_to_fastapi(
    app,
    agent_card_routes=agent_card_routes,
    jsonrpc_routes=jsonrpc_routes,
)
