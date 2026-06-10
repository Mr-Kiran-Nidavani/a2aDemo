# A2A Protocol Demo — Weather + Stock Agents

A complete implementation of the [Agent2Agent (A2A) Protocol](https://a2a-protocol.org) using the official Python SDK (`a2a-sdk`). Two independent remote agents each declare their own skills via an Agent Card. A client discovers them at runtime, matches the user query to the right skill, and routes directly — **no orchestrator, no hardcoded routing**.

The key point of this demo: **each agent is built with a different AI framework**, but they all speak the same A2A protocol. The client doesn't know or care which framework powers each agent.

| Agent | Framework | LLM | Port |
|---|---|---|---|
| Weather Agent | **Google ADK** + `to_a2a()` | GPT-3.5 via LiteLLM | 8001 |
| Stock Agent | **LangChain** + manual A2A bridge | GPT-3.5 via ChatOpenAI | 8002 |

---

## Table of Contents

1. [What is A2A?](#1-what-is-a2a)
2. [Project Overview](#2-project-overview)
3. [How Different Frameworks Integrate with A2A](#3-how-different-frameworks-integrate-with-a2a)
4. [Installation](#4-installation)
5. [How to Run](#5-how-to-run)
6. [File-Level Explanation](#6-file-level-explanation)
7. [How the Client Discovers Remote Agents](#7-how-the-client-discovers-remote-agents)
8. [How a User Request is Served — End to End](#8-how-a-user-request-is-served--end-to-end)
9. [Project Structure](#9-project-structure)
10. [Sample Requests and Responses](#10-sample-requests-and-responses)
11. [Endpoints Reference](#11-endpoints-reference)

---

## 1. What is A2A?

**A2A (Agent-to-Agent)** is an open standard that lets AI agents discover each other and communicate over HTTP using JSON-RPC 2.0.

| Protocol | Used for |
|---|---|
| HTTP | Browsers talking to web servers |
| MCP | AI models talking to tools |
| **A2A** | **AI agents talking to other AI agents** |

Key ideas:
- Each agent publishes a machine-readable **Agent Card** at `/.well-known/agent-card.json`
- Clients discover agents by fetching that card and reading its skill tags
- Communication is JSON-RPC over HTTP — framework-agnostic
- **Any agent framework can participate** as long as it exposes an A2A-compliant endpoint

---

## 2. Project Overview

```
┌─────────────────────────────────────────────────────┐
│  client_demo.py  /  ui.py  (A2A Client)             │
│                                                     │
│  1. Fetch agent cards from port 8001 and 8002       │
│  2. Match user query against skill tags             │
│  3. Send message directly to the matched agent      │
└────────────────────┬────────────────────────────────┘
                     │ A2A JSON-RPC (POST /)
          ┌──────────┴──────────┐
          ▼                     ▼
┌──────────────────────┐  ┌──────────────────────────┐
│  Weather Agent       │  │  Stock Agent             │
│  port 8001           │  │  port 8002               │
│                      │  │                          │
│  Framework: ADK      │  │  Framework: LangChain    │
│  to_a2a() auto-wires │  │  Manual A2A bridge       │
│  A2A protocol        │  │  AgentExecutor subclass  │
│                      │  │                          │
│  tags: weather,      │  │  tags: stock, aapl,      │
│  rain, cloudy...     │  │  tsla, nvda...           │
└──────────────────────┘  └──────────────────────────┘
```

---

## 3. How Different Frameworks Integrate with A2A

This is the core learning of this demo. A2A is a **protocol**, not a framework. Any agent — regardless of how it's built — can participate by exposing A2A-compliant HTTP endpoints. There are two integration approaches shown here.

---

### Approach 1 — Google ADK: `to_a2a()` (Weather Agent)

Google ADK has first-class A2A support. The `to_a2a()` function wraps any ADK `Agent` and automatically:
- Creates an `A2aAgentExecutor` that bridges A2A ↔ ADK runner
- Sets up in-memory task, session, and artifact stores
- Mounts all A2A routes including `/.well-known/agent-card.json`
- Returns a Starlette ASGI app ready for uvicorn

**Step 1 — Define the ADK agent** (`remoteAgents/weather/agent.py`):
```python
from google.adk.agents import Agent
from google.adk.models.lite_llm import LiteLlm

root_agent = Agent(
    model=LiteLlm(model="openai/gpt-3.5-turbo", api_key=os.getenv("OPENAI_API_KEY")),
    name="weather_agent",
    instruction="You are a helpful weather assistant...",
    tools=[get_weather],   # plain Python function — ADK wraps it as a tool
)
```

**Step 2 — Expose via A2A** (`remoteAgents/weather/server.py`):
```python
from google.adk.a2a.utils.agent_to_a2a import to_a2a
from a2a.types import AgentCard, AgentSkill, AgentCapabilities

agent_card = AgentCard(
    name="Weather Agent",
    url="http://localhost:8001",
    preferred_transport="JSONRPC",
    capabilities=AgentCapabilities(streaming=False),
    default_input_modes=["text/plain"],
    default_output_modes=["text/plain"],
    skills=[
        AgentSkill(
            id="weather_lookup",
            name="Weather Lookup",
            tags=["weather", "temperature", "rain", "cloudy", "wind", ...],
            ...
        )
    ],
    ...
)

# One line — entire A2A server is ready
app = to_a2a(root_agent, port=8001, agent_card=agent_card)
```

That's it. ADK handles everything — the agent card endpoint, JSON-RPC dispatcher, task lifecycle, and tool execution loop.

---

### Approach 2 — LangChain: Manual A2A Bridge (Stock Agent)

For frameworks without built-in A2A support, you implement the A2A `AgentExecutor` interface and manually manage the task lifecycle. The framework does the LLM work; your bridge code translates it into A2A events.

**The A2A task lifecycle** (your bridge must implement this):
```
1. new_task(message)             → create A2A Task, enqueue it
2. update_status(working)        → tell client "I'm processing"
3. [your framework does its work]
4. add_artifact(result_text)     → attach the answer
5. update_status(completed)      → signal done
```

**Step 1 — Define the LangChain tool and model** (`remoteAgents/stock/agent_executor.py`):
```python
from langchain_openai import ChatOpenAI
from langchain_core.tools import tool

@tool
def get_stock(symbol: str) -> str:
    """Returns stock price, sentiment and note for a ticker."""
    ...

# Two LLM instances: one with tools (for tool selection), one plain (for formatting)
_llm_with_tools = ChatOpenAI(model="gpt-3.5-turbo", ...).bind_tools([get_stock])
_llm = ChatOpenAI(model="gpt-3.5-turbo", ...)
```

**Step 2 — Implement the A2A bridge** (`remoteAgents/stock/agent_executor.py`):
```python
from a2a.server.agent_execution.agent_executor import AgentExecutor

class StockAgentExecutor(AgentExecutor):
    async def execute(self, context: RequestContext, event_queue: EventQueue) -> None:
        # A2A task lifecycle — mandatory
        task = context.current_task or new_task(context.message)
        updater = TaskUpdater(event_queue, task.id, task.context_id)
        await updater.update_status(TaskState.working, ...)

        # LangChain does the work
        response = await _llm_with_tools.ainvoke([HumanMessage(content=user_text)])
        if response.tool_calls:
            tool_result = get_stock.invoke(response.tool_calls[0]["args"])
            final = await _llm.ainvoke([HumanMessage(content=f"Format: {tool_result}")])
            result_text = final.content
        else:
            result_text = response.content

        # Return result via A2A artifact
        await updater.add_artifact(parts=[Part(root=TextPart(text=result_text))], ...)
        await updater.update_status(TaskState.completed, ...)
```

**Step 3 — Wire to FastAPI** (`remoteAgents/stock/server.py`):
```python
from a2a.server.apps import A2AFastAPIApplication
from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.tasks.inmemory_task_store import InMemoryTaskStore

handler = DefaultRequestHandler(
    agent_executor=StockAgentExecutor(),
    task_store=InMemoryTaskStore(),
)

app = FastAPI(...)
A2AFastAPIApplication(agent_card=agent_card, http_handler=handler).add_routes_to_app(app)
```

---

### Framework comparison

| | Google ADK | LangChain (or any other framework) |
|---|---|---|
| **A2A wiring** | `to_a2a()` — one line | Manual `AgentExecutor` subclass |
| **Task lifecycle** | Handled automatically | You implement 5 steps |
| **Tool integration** | Pass function directly to `Agent(tools=[...])` | `@tool` decorator + `bind_tools()` |
| **Server type** | Starlette (via `to_a2a`) | FastAPI (your choice) |
| **Agent card** | Auto-generated or custom | You define it manually |
| **Effort** | Minimal | ~60 lines of bridge code |

---

## 4. Installation

```bash
# Install uv (fast Python package manager)
pip install uv

# Create venv and install all dependencies
uv venv
uv sync

# Activate
.venv\Scripts\activate          # Windows
source .venv/bin/activate       # Mac / Linux
```

Set your API key in `.env`:
```
OPENAI_API_KEY=sk-your-key-here
```

---

## 5. How to Run

### Option A — Streamlit UI (recommended)

```bash
# Terminal 1 — start both agents
python main.py

# Terminal 2 — start the UI
streamlit run ui.py
```

Opens at **http://localhost:8501**. Use the **"Show request trace"** toggle to see the full A2A flow live.

### Option B — CLI

```bash
python main.py        # Terminal 1
python client_demo.py # Terminal 2
```

### Troubleshooting — port in use

```bash
netstat -ano | findstr ":8001"
taskkill /PID <PID> /F
```

---

## 6. File-Level Explanation

---

### `main.py` — Starting point of the application

Starts both remote A2A agent servers concurrently using `asyncio` + `uvicorn`.

#### `SERVERS`
Stores configuration for each agent (app path, host, port, label):
```python
SERVERS = [
    {"app": "remoteAgents.weather.server:app", "host": "0.0.0.0", "port": 8001, "label": "Weather Agent"},
    {"app": "remoteAgents.stock.server:app",   "host": "0.0.0.0", "port": 8002, "label": "Stock Agent"},
]
```

#### `serve(config: dict)`
Creates and starts a uvicorn server asynchronously:
```python
async def serve(config: dict) -> None:
    cfg = uvicorn.Config(app=config["app"], host=config["host"], port=config["port"], log_level="info")
    server = uvicorn.Server(cfg)
    await server.serve()
```

#### `main()`
Starts all servers concurrently — neither blocks the other:
```python
await asyncio.gather(*[serve(s) for s in SERVERS])
```

#### Purpose
Clients discover agents via their agent cards and communicate directly with the appropriate agent based on skill tags — no central orchestrator involved.

---

### `ui.py` — Streamlit chat interface

Streamlit UI that takes user input and calls either:
- `run_agent_with_trace(message)` — shows live A2A flow steps in a side panel (trace mode ON)
- `run_agent(message)` — direct call, just returns the answer (trace mode OFF)

Both functions live in `clientAgent/runner.py` and `clientAgent/tracer.py`.

---

### `clientAgent/runner.py` — A2A client logic

Handles discovery, message building, sending, and response extraction.

#### `_build_message()`
Builds a `Message` object using the SDK helper:
```python
from a2a.client.helpers import create_text_message_object

def _build_message(user_message: str, context_id: str | None = None):
    msg = create_text_message_object(content=user_message)
    msg.message_id = uuid4().hex
    msg.context_id = context_id or uuid4().hex
    return msg
```

#### `run_agent()`
Discovers the right agent and sends the message:
```python
async with httpx.AsyncClient(timeout=60.0) as http_client:
    _, card, _ = await discover_and_match(user_message, http_client)

    config = ClientConfig(httpx_client=http_client, streaming=False)
    client = ClientFactory(config).create(card)

    async for event in client.send_message(message):   # async generator — no await
        text = _extract_text_from_event(event)
        if text:
            final_text = text
```

- `async with httpx.AsyncClient(...)` — opens an HTTP client, closes it when the block exits
- `client.send_message(message)` returns an **async generator** directly (not a coroutine) — iterate with `async for`, no `await`

#### `_extract_text_from_event()`
The new SDK returns `ClientEvent = tuple[Task, UpdateEvent]` or a `Message`. Text is extracted from task artifacts:
```python
def _extract_text_from_event(event) -> str:
    if isinstance(event, tuple):
        task, update = event
        if isinstance(update, TaskArtifactUpdateEvent):
            texts = get_text_parts(update.artifact.parts)
            if texts:
                return texts[-1]
        if isinstance(task, Task) and task.artifacts:
            for artifact in reversed(task.artifacts):
                texts = get_text_parts(artifact.parts)
                if texts:
                    return texts[-1]
    elif isinstance(event, Message):
        texts = get_text_parts(event.parts)
        if texts:
            return texts[-1]
    return ""
```

---

### `clientAgent/discovery.py` — Agent discovery and skill matching

Responsible for finding the right remote agent for a given user query.

#### `discover_and_match()`
```python
async def discover_and_match(query, http_client):
    for base_url in REMOTE_AGENT_URLS:
        try:
            resolver = A2ACardResolver(httpx_client=http_client, base_url=base_url)
            card = await resolver.get_agent_card()   # GET /.well-known/agent-card.json
            skill = match_skill(query, card)          # check skill tags
            if skill is not None:
                return skill, card, base_url
        except Exception:
            continue
    return None, None, None
```

- Uses `A2ACardResolver` from `a2a.client` to fetch `/.well-known/agent-card.json`
- `match_skill()` iterates over `card.skills` and checks if any `skill.tags` appear in the query (case-insensitive)
- The endpoint URL comes from `card.url` — no hardcoded routing

---

### `remoteAgents/weather/` — Google ADK Agent

#### `agent.py` — ADK agent definition
```python
from google.adk.agents import Agent
from google.adk.models.lite_llm import LiteLlm

root_agent = Agent(
    model=LiteLlm(model="openai/gpt-3.5-turbo", api_key=os.getenv("OPENAI_API_KEY")),
    name="weather_agent",
    instruction="You are a helpful weather assistant...",
    tools=[get_weather],   # plain Python function — ADK wraps it automatically
)
```

#### `server.py` — A2A exposure via `to_a2a()`
```python
from google.adk.a2a.utils.agent_to_a2a import to_a2a

agent_card = AgentCard(
    name="Weather Agent",
    url="http://localhost:8001",
    preferred_transport="JSONRPC",
    skills=[AgentSkill(id="weather_lookup", tags=["weather", "rain", "cloudy", ...], ...)],
    ...
)

app = to_a2a(root_agent, port=8001, agent_card=agent_card)
# Returns a Starlette ASGI app — uvicorn runs it directly
```

`to_a2a()` automatically handles the full A2A server setup. No executor, no handler, no route wiring needed.

#### `weather_tool.py` — mock data tool
Plain Python function that returns weather data for Indian cities. ADK picks it up via `tools=[get_weather]`.

---

### `remoteAgents/stock/` — LangChain Agent

#### `agent_executor.py` — LangChain + A2A bridge

Defines the LangChain tool, model, and the A2A `AgentExecutor` bridge.

**Tool definition:**
```python
from langchain_core.tools import tool

@tool
def get_stock(symbol: str) -> str:
    """Returns stock price, sentiment and note for a ticker."""
    d = _get_stock_data(symbol)
    return f"{d['symbol']}: ${d['price']} | {d['sentiment']} | {d['note']}"
```

**Two LLM instances** (to avoid tool-binding interfering with the formatting step):
```python
_llm_with_tools = ChatOpenAI(model="gpt-3.5-turbo", ...).bind_tools([get_stock])
_llm = ChatOpenAI(model="gpt-3.5-turbo", ...)   # plain — for final answer formatting
```

**A2A bridge — the 5-step task lifecycle:**
```python
class StockAgentExecutor(AgentExecutor):
    async def execute(self, context, event_queue):
        task = context.current_task or new_task(context.message)
        updater = TaskUpdater(event_queue, task.id, task.context_id)

        await updater.update_status(TaskState.working, ...)         # step 2

        response = await _llm_with_tools.ainvoke([...])             # step 3a — tool selection
        if response.tool_calls:
            tool_result = get_stock.invoke(response.tool_calls[0]["args"])  # step 3b — tool call
            final = await _llm.ainvoke([...format prompt...])       # step 3c — format answer
            result_text = final.content

        await updater.add_artifact(parts=[...result_text...], ...)  # step 4
        await updater.update_status(TaskState.completed, ...)       # step 5
```

#### `server.py` — FastAPI + A2AFastAPIApplication
```python
from a2a.server.apps import A2AFastAPIApplication
from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.tasks.inmemory_task_store import InMemoryTaskStore

agent_card = AgentCard(
    name="Stock Agent",
    url="http://localhost:8002",
    preferred_transport="JSONRPC",
    skills=[AgentSkill(id="stock_analysis", tags=["stock", "aapl", "tsla", ...], ...)],
    ...
)

handler = DefaultRequestHandler(
    agent_executor=StockAgentExecutor(),
    task_store=InMemoryTaskStore(),
)

app = FastAPI(...)
A2AFastAPIApplication(agent_card=agent_card, http_handler=handler).add_routes_to_app(app)
# Mounts: POST / (JSON-RPC) + GET /.well-known/agent-card.json
```

#### `stock_tool.py` — mock data tool
Plain Python function with mock stock data for AAPL, TSLA, NVDA, etc. Called by the LangChain `@tool`.

---

## 7. How the Client Discovers Remote Agents

**Step 1 — Fetch agent cards**

`A2ACardResolver` fetches `/.well-known/agent-card.json` from each known base URL:
```python
resolver = A2ACardResolver(httpx_client=http_client, base_url="http://localhost:8001")
card = await resolver.get_agent_card()
```

**Step 2 — Match query against skill tags**
```python
def match_skill(query: str, card) -> AgentSkill | None:
    query_lower = query.lower()
    for skill in (card.skills or []):
        for tag in (skill.tags or []):
            if tag.lower() in query_lower:
                return skill   # first match wins
    return None
```

Example: `"weather in Mumbai"` → tag `"weather"` found in Weather Agent's skills → Weather Agent selected.

**Step 3 — Get endpoint from card**
```python
def card_url(card) -> str:
    return card.url   # e.g. "http://localhost:8001"
```

No hardcoded URL mappings — the card is the source of truth.

---

## 8. How a User Request is Served — End to End

**Example: `"Should I buy AAPL?"`**

```
User types: "Should I buy AAPL?"
      │
      ▼  clientAgent/runner.py
      │  discover_and_match() → tag "aapl" matches Stock Agent
      │  ClientFactory(config).create(card) → builds JSON-RPC client
      │  client.send_message(message) → POST http://localhost:8002/
      │
      ▼  remoteAgents/stock/server.py
      │  A2AFastAPIApplication → DefaultRequestHandler → StockAgentExecutor.execute()
      │
      ▼  remoteAgents/stock/agent_executor.py  (LangChain bridge)
      │  update_status(working)
      │  _llm_with_tools.ainvoke("Should I buy AAPL?")
      │    → tool_calls: [get_stock("AAPL")]
      │  get_stock.invoke({"symbol": "AAPL"})
      │    → "AAPL: $189.30 ▲1.20 (+0.64%) | bullish | Strong iPhone demand..."
      │  _llm.ainvoke("Format as 3-line analysis: ...")
      │    → "AAPL is at $189.30, up $1.20 today.\nBullish — strong iPhone demand.\nGood Buy."
      │  add_artifact(result_text)
      │  update_status(completed)
      │
      ▼  clientAgent/runner.py
      │  _extract_text_from_event() reads text from Task artifact
      │
      ▼  User sees: "AAPL is at $189.30, up $1.20 today. ..."
```

The weather flow is identical except ADK handles the tool call internally — no manual bridge code.

---

## 9. Project Structure

```
a2aDemo/
│
├── main.py              ← Starts both remote agents (port 8001, 8002)
├── client_demo.py       ← CLI client: discovery → match → send → print
├── ui.py                ← Streamlit chat UI with live A2A trace panel
│
├── clientAgent/
│   ├── discovery.py     ← A2ACardResolver + match_skill + discover_and_match
│   ├── runner.py        ← ClientFactory + send_message + text extraction
│   └── tracer.py        ← Same as runner but yields live trace steps for the UI
│
└── remoteAgents/
    ├── weather/                  ← Google ADK agent
    │   ├── agent.py              ← ADK Agent(model=LiteLlm(...), tools=[get_weather])
    │   ├── server.py             ← to_a2a(root_agent, agent_card=...) → Starlette app
    │   └── weather_tool.py       ← get_weather() mock data
    └── stock/                    ← LangChain agent
        ├── agent_executor.py     ← @tool + ChatOpenAI + A2A AgentExecutor bridge
        ├── server.py             ← A2AFastAPIApplication + DefaultRequestHandler
        └── stock_tool.py         ← get_stock() mock data
```

---

## 10. Sample Requests and Responses

Send to `POST /` via Postman or curl.

### Weather — port 8001

```json
{
  "jsonrpc": "2.0",
  "id": "1",
  "method": "message/send",
  "params": {
    "message": {
      "role": "user",
      "messageId": "abc123",
      "parts": [{ "text": "What is the weather in Bangalore?" }]
    }
  }
}
```

Response artifact text:
```
The weather in Bangalore is currently 26°C and Cloudy with 72% humidity and winds of 12 km/h.
```

### Stock — port 8002

```json
{
  "jsonrpc": "2.0",
  "id": "2",
  "method": "message/send",
  "params": {
    "message": {
      "role": "user",
      "messageId": "def456",
      "parts": [{ "text": "Should I buy AAPL?" }]
    }
  }
}
```

Response artifact text:
```
AAPL is at $189.30, up $1.20 (0.64%) today.
Bullish — strong iPhone demand and services growth driving consistent revenue.
Good Buy — solid fundamentals and long-term growth trajectory support investment.
```

### Available cities
`Bangalore` `Mumbai` `Delhi` `Chennai` `Hyderabad` `Kolkata` `Pune`

### Available stocks
`AAPL` `TSLA` `GOOGL` `MSFT` `AMZN` `NVDA` `META` `NFLX` `RELIANCE` `TCS` `INFY`

---

## 11. Endpoints Reference

### Weather Agent — port 8001 (Google ADK)

| Method | URL | Description |
|---|---|---|
| GET | `/.well-known/agent-card.json` | A2A discovery — AgentCard with weather skills |
| POST | `/` | A2A JSON-RPC — `message/send` → returns task with artifact |
| GET | `/docs` | Swagger UI |

### Stock Agent — port 8002 (LangChain)

| Method | URL | Description |
|---|---|---|
| GET | `/.well-known/agent-card.json` | A2A discovery — AgentCard with stock skills |
| POST | `/` | A2A JSON-RPC — `message/send` → returns task with artifact |
| GET | `/docs` | Swagger UI |
