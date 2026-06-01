# 🌐 A2A (Agent-to-Agent) + Google ADK Complete Guide

This project demonstrates how to build an **AI Agent using Google ADK** and expose it using the **A2A (Agent-to-Agent) protocol** via FastAPI.

It allows AI agents to communicate using a standard JSON-RPC format.

---

# 🧠 WHAT IS A2A?

A2A (Agent-to-Agent) is a protocol that enables:

- 🤖 AI agents to talk to other AI agents
- 🔁 Standard communication using JSON-RPC
- 🌐 HTTP-based agent networking

Think of it as:

HTTP → Web apps  
MCP → Tools  
A2A → Agents

---

# 🔁 HOW A2A WORKS

```text
Client (Agent/UI/Postman)
        |
        | JSON-RPC request
        v
FastAPI A2A Server
        |
        | extracts message
        v
ADK Runner
        |
        | calls LLM + tools
        v
ADK Agent (Brain)
        |
        | uses tools
        v
Response → back to client
```
---

# 📁 PROJECT STRUCTURE
```text
a2aDemo/
├── .env
├── requirements.txt
│
├── a2a/
│   ├── __init__.py
│   ├── server.py
│   ├── agent_card.py
│   └── runner.py
│
├── agents/
│   └── weather/
│       ├── __init__.py
│       ├── agent.py
│       └── weather_tool.py
│
└── README.md
```
---

# ⚙️ TECHNOLOGY STACK

- Python 3.10+
- FastAPI
- Google ADK (v2.1.0)
- LiteLLM (OpenAI / Gemini)
- Pydantic
- Uvicorn

---

# 🧠 AGENT (BRAIN)

agents/weather/agent.py

```python
from google.adk.agents.llm_agent import Agent
from google.adk.models.lite_llm import LiteLlm
from .weather_tool import get_weather
import os

model = LiteLlm(
    model="openai/gpt-3.5-turbo",
    api_key=os.getenv("OPENAI_API_KEY")
)

root_agent = Agent(
    model=model,
    name="weather_agent",
    description="Weather assistant",
    instruction="Answer weather questions using tools",
    tools=[get_weather]
)
```
---

# 🔧 WEATHER TOOL

agents/weather/weather_tool.py
```python
def get_weather(city: str):
    data = {
        "bangalore": "26°C cloudy",
        "mumbai": "31°C humid",
        "delhi": "35°C sunny"
    }
    return data.get(city.lower(), f"No data for {city}")
```
---

# 📡 AGENT CARD (DISCOVERY LAYER)

a2a/agent_card.py

```python
AGENT_CARD = {
    "name": "weather_agent",
    "description": "Weather assistant using ADK",
    "version": "1.0.0",
    "skills": [
        {
            "id": "weather_lookup",
            "name": "Weather Lookup",
            "description": "Returns weather for cities"
        }
    ]
}
```
---

# ⚙️ RUNNER (ADK BRIDGE)

a2a/runner.py

```python
import uuid
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

from agents.weather.agent import root_agent

APP_NAME = "weather_app"

session_service = InMemorySessionService()

runner = Runner(
    agent=root_agent,
    app_name=APP_NAME,
    session_service=session_service
)

async def run_agent(user_message: str):

    session_id = str(uuid.uuid4())

    session_service.create_session(
        app_name=APP_NAME,
        user_id="a2a_user",
        session_id=session_id
    )

    message = types.Content(
        role="user",
        parts=[types.Part(text=user_message)]
    )

    final_response = ""

    async for event in runner.run_async(
        user_id="a2a_user",
        session_id=session_id,
        new_message=message
    ):
        if event.content and event.content.parts:
            final_response = event.content.parts[0].text

    return final_response
```
---

# 🌐 A2A SERVER (FASTAPI)

a2a/server.py

```python
from fastapi import FastAPI
from pydantic import BaseModel
from typing import List

from a2a.agent_card import AGENT_CARD
from a2a.runner import run_agent

app = FastAPI(title="Weather A2A Server")

@app.get("/.well-known/agent.json")
async def agent_card():
    return AGENT_CARD

@app.get("/health")
async def health():
    return {"status": "ok"}

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
```
---

# 🔑 ENV FILE

OPENAI_API_KEY=your_api_key_here

---

# 📦 INSTALLATION

pip install fastapi uvicorn google-adk pydantic python-dotenv

---

# ▶️ RUN SERVER

uvicorn a2a.server:app --reload

---

# 📍 ENDPOINTS

GET /.well-known/agent.json
GET /health
POST /a2a

---

# 🧪 SAMPLE REQUEST

```json
{
  "jsonrpc": "2.0",
  "id": "1",
  "method": "message/send",
  "params": {
    "message": {
      "role": "user",
      "parts": [
        {
          "type": "text",
          "text": "weather in bangalore"
        }
      ]
    }
  }
}
```
---

# 🔥 SAMPLE RESPONSE
```json
{
  "jsonrpc": "2.0",
  "id": "1",
  "result": {
    "status": "completed",
    "message": {
      "role": "agent",
      "parts": [
        {
          "type": "text",
          "text": "26°C cloudy"
        }
      ]
    }
  }
}
```
---

# 🚀 WHY A2A IS IMPORTANT

Without A2A:
Agent A → custom integration → Agent B

With A2A:
Any Agent → standard protocol → Any Agent

Benefits:
- Interoperability
- Multi-agent systems
- Scalable AI networks
- Plug & play agents

---

# 🧭 SUMMARY

agent.py → Brain (LLM)  
weather_tool.py → Actions  
agent_card.py → Discovery  
runner.py → ADK bridge  
server.py → A2A API layer  

---

# 🎯 NEXT STEPS

- Multi-agent system (weather + hotel + flight)
- Streaming (SSE)
- Real APIs (OpenWeatherMap)
- Auth (JWT/API key)
- Docker deployment