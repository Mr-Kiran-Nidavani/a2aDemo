"""
A2A Server — single endpoint, single port (8000).
The client only ever talks here. Routing happens internally via the orchestrator.
"""
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional

from clientAgent.agent_card import AGENT_CARD
from clientAgent.runner import run_agent
from remoteAgents.orchestrator.agent import orchestrator


app = FastAPI(
    title="A2A Multi-Agent Demo",
    description=(
        "A2A protocol server with an orchestrator that routes requests "
        "to a Weather Agent or Stock Agent based on user intent."
    ),
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── A2A Protocol Models ───────────────────────────────────────────────────────

class A2AMessagePart(BaseModel):
    type: str   # "text"
    text: str


class A2AMessage(BaseModel):
    role: str   # "user" | "agent"
    parts: List[A2AMessagePart]


class A2AParams(BaseModel):
    message: A2AMessage
    sessionId: Optional[str] = None
    metadata: Optional[dict] = None


class A2ARequest(BaseModel):
    jsonrpc: str = "2.0"
    id: str
    method: str  # "message/send"
    params: A2AParams


# ── Endpoints ─────────────────────────────────────────────────────────────────

@app.get("/.well-known/agent.json", summary="Agent Card — A2A Discovery")
async def agent_card():
    """
    Clients discover the agent's capabilities here before sending messages.
    Lists both weather and stock skills exposed through the orchestrator.
    """
    return AGENT_CARD


@app.get("/health", summary="Health Check")
async def health():
    return {
        "status": "ok",
        "agent": orchestrator.name,
        "sub_agents": ["weather_agent", "stock_agent"],
        "protocol": "A2A",
        "version": "1.0.0"
    }


@app.post("/a2a", summary="A2A Message Endpoint")
async def a2a_endpoint(body: A2ARequest):
    """
    Single A2A endpoint. Accepts any user message.
    The orchestrator internally routes to the right agent.

    Supported intents:
    - Weather: 'weather in Bangalore', 'how is the weather in Mumbai'
    - Stock:   'analyse AAPL', 'should I buy TSLA', 'NVDA price'
    """
    if body.method != "message/send":
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported method '{body.method}'. Use 'message/send'."
        )

    if not body.params.message.parts:
        raise HTTPException(status_code=400, detail="Message must have at least one part.")

    user_text = body.params.message.parts[0].text.strip()

    if not user_text:
        raise HTTPException(status_code=400, detail="Message text cannot be empty.")

    result = await run_agent(user_text)

    return {
        "jsonrpc": "2.0",
        "id": body.id,
        "result": {
            "status": "completed",
            "message": {
                "role": "agent",
                "parts": [{"type": "text", "text": result}]
            }
        }
    }
