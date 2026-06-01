from fastapi import FastAPI, Request
from a2a.agent_card import AGENT_CARD
from a2a.runner import run_agent
from pydantic import BaseModel
from typing import List, Dict, Any
from agents.weather.agent import root_agent

app = FastAPI()


class A2AMessagePart(BaseModel):
    type: str
    text: str


class A2AMessage(BaseModel):
    role: str
    parts: List[A2AMessagePart]


class A2AParams(BaseModel):
    message: A2AMessage


class A2ARequest(BaseModel):
    jsonrpc: str
    id: str
    method: str
    params: A2AParams

@app.get("/.well-known/agent.json")
async def agent_card():
    return AGENT_CARD


@app.get("/health")
async def health():
    return {
        "status": "ok",
        "agent": root_agent.name
    }



@app.post("/a2a")
async def a2a_endpoint(body: A2ARequest):
    user_text = body.params.message.parts[0].text

    result = await run_agent(user_text)

    return {
        "jsonrpc": "2.0",
        "id": body.id,
        "result": {
            "status": "completed",
            "message": {
                "role": "agent",
                "parts": [
                    {
                        "type": "text",
                        "text": result
                    }
                ]
            }
        }
    }