# A2A Protocol Demo — Weather + Stock Agents

A complete implementation of the [Agent2Agent (A2A) Protocol](https://a2a-protocol.org) using the official Python SDK (`a2a-sdk`). Two independent remote agents each declare their own skills. A client discovers them at runtime, matches the user query to the right skill, and routes directly — no orchestrator, no hardcoded routing.

---

## Table of Contents

1. [What is A2A?](#1-what-is-a2a)
2. [Project Overview](#2-project-overview)
3. [Installation](#3-installation)
4. [How to Run](#4-how-to-run)
5. [How Remote Agents Define Their Skills](#5-how-remote-agents-define-their-skills)
6. [How the Client Discovers Remote Agents](#6-how-the-client-discovers-remote-agents)
7. [How a User Request is Served — End to End](#7-how-a-user-request-is-served--end-to-end)
8. [Project Structure](#8-project-structure)
9. [Sample Requests and Responses](#9-sample-requests-and-responses)
10. [Endpoints Reference](#10-endpoints-reference)

---

## 1. What is A2A?

**A2A (Agent-to-Agent)** is an open standard (donated to the Linux Foundation by Google) that lets AI agents discover each other and communicate over HTTP using JSON-RPC 2.0.

| Protocol | Used for |
|---|---|
| HTTP | Browsers talking to web servers |
| MCP | AI models talking to tools |
| **A2A** | **AI agents talking to other AI agents** |

The key ideas:
- Each agent publishes a machine-readable **Agent Card** describing its skills
- Clients discover agents by fetching that card from `/.well-known/agent-card.json`
- Communication happens over JSON-RPC — standard, framework-agnostic

---

## 2. Project Overview

Two independent A2A servers and one client:

```
┌─────────────────────────────────────────────────────┐
│  client_demo.py  /  ui.py  (A2A Client)             │
│                                                     │
│  1. Fetches agent cards from port 8001 and 8002     │
│  2. Reads skill tags from each card                 │
│  3. Matches user query → picks the right agent      │
│  4. Sends message directly to that agent            │
└────────────────────┬────────────────────────────────┘
                     │ A2A JSON-RPC
          ┌──────────┴──────────┐
          ▼                     ▼
┌─────────────────┐   ┌─────────────────┐
│  Weather Agent  │   │  Stock Agent    │
│  port 8001      │   │  port 8002      │
│                 │   │                 │
│  Skill:         │   │  Skill:         │
│  weather_lookup │   │  stock_analysis │
│  tags: weather, │   │  tags: stock,   │
│  rain, cloudy.. │   │  aapl, tsla...  │
└─────────────────┘   └─────────────────┘
```

There is **no orchestrator**. The client itself does discovery and routing — this is exactly how the A2A protocol is designed to work.

---

## 3. Installation

**Step 1 — Install uv** (fast Python package manager):
```bash
pip install uv
```

**Step 2 — Create virtual environment:**
```bash
uv venv
```

**Step 3 — Activate:**
```bash
# Windows
.venv\Scripts\activate

# Mac / Linux
source .venv/bin/activate
```

**Step 4 — Install dependencies:**
```bash
uv pip install -r requirements.txt
```

**Step 5 — Set your API key** in `.env`:
```
OPENAI_API_KEY=sk-your-key-here
```

---

## 4. How to Run

### Option A — Streamlit UI (recommended)

Shows each A2A step live as the request flows through the system.

```bash
# Terminal 1 — start both remote agents
python main.py

# Terminal 2 — start the UI
streamlit run ui.py
```

Opens at **http://localhost:8501**

Use the **"Show request trace"** toggle in the sidebar:
- **ON** — live trace showing discovery, skill matching, tool call, response
- **OFF** — simple chat, no trace overhead

---

### Option B — CLI Client

```bash
# Terminal 1
python main.py

# Terminal 2
python client_demo.py
```

The CLI client will:
1. Fetch agent cards from both agents (Step 1 — Discovery)
2. Print each agent's name, skills, and example queries
3. Run 6 sample queries — matching each to the right agent automatically
4. Print the routing decision and response for each query

---

### Option C — Swagger UI (manual testing)

```bash
python main.py
```

Then open:
- `http://localhost:8001/docs` — Weather Agent
- `http://localhost:8002/docs` — Stock Agent

Use the `POST /` endpoint with the JSON body from the [Sample Requests](#9-sample-requests-and-responses) section.

---

## 5. How Remote Agents Define Their Skills

Each remote agent defines an `AgentCard` with one or more `AgentSkill` objects. This is the A2A "self-registration" — the agent tells the world what it can do.

### AgentSkill — the unit of capability

```python
# remoteAgents/weather/server.py
AgentSkill(
    id="weather_lookup",              # unique identifier
    name="Weather Lookup",            # human-readable label
    description="Current weather conditions for a city",
    tags=["weather", "temperature", "rain", "cloudy", "wind", ...],  # ← discovery keys
    examples=["What is the weather in Bangalore?", "Is it raining in Delhi?"],
    input_modes=["text/plain"],        # accepted MIME types
    output_modes=["text/plain"],       # returned MIME types
)
```

**`tags` are the discovery keys.** The client matches the user's query against these. If the query contains any tag word, this skill — and its agent — is selected.

### AgentCard — the agent's business card

```python
# remoteAgents/weather/server.py
agent_card = AgentCard(
    name="Weather Agent",
    description="Provides current weather conditions for Indian cities.",
    version="1.0.0",
    capabilities=AgentCapabilities(streaming=False),
    default_input_modes=["text/plain"],
    default_output_modes=["text/plain"],
    supported_interfaces=[
        AgentInterface(
            url="http://localhost:8001",   # where to send requests
            protocol_binding="JSONRPC",    # communication protocol
        )
    ],
    skills=[weather_skill],  # list of AgentSkill objects
)
```

### How the card is published automatically

`create_agent_card_routes` exposes the card at `/.well-known/agent-card.json` — no extra code needed:

```python
# remoteAgents/weather/server.py
handler = DefaultRequestHandler(
    agent_executor=WeatherAgentExecutor(),
    task_store=InMemoryTaskStore(),
    agent_card=agent_card,
)

agent_card_routes = create_agent_card_routes(agent_card)   # ← serves /.well-known/agent-card.json
jsonrpc_routes    = create_jsonrpc_routes(handler, rpc_url="/")  # ← serves POST /

add_a2a_routes_to_fastapi(app, agent_card_routes=agent_card_routes, jsonrpc_routes=jsonrpc_routes)
```

The stock agent follows the exact same pattern on port 8002 with its own skills.

---

## 6. How the Client Discovers Remote Agents

The client uses `A2ACardResolver` — the official A2A SDK class for the Well-Known URI discovery strategy.

### Step 1 — Fetch each agent's card

```python
# clientAgent/discovery.py
resolver = A2ACardResolver(
    httpx_client=http_client,
    base_url="http://localhost:8001",
)
card = await resolver.get_agent_card()
# Fetches GET http://localhost:8001/.well-known/agent-card.json
# Returns a typed AgentCard protobuf object
```

This is done for every URL in `REMOTE_AGENT_URLS = ["http://localhost:8001", "http://localhost:8002"]`.

### Step 2 — Match query against skill tags

```python
# clientAgent/discovery.py
def match_skill(query: str, card) -> AgentSkill | None:
    query_lower = query.lower()
    for skill in (card.skills or []):
        for tag in (skill.tags or []):
            if tag.lower() in query_lower:
                return skill   # first match wins
    return None
```

Example: query `"weather in Bangalore"` → tag `"weather"` found in WeatherAgent's skills → WeatherAgent selected.

### Step 3 — Read the endpoint URL from the card itself

No hardcoded URL mappings. The URL comes directly from the card:

```python
# clientAgent/discovery.py
def card_url(card) -> str:
    return card.supported_interfaces[0].url   # e.g. "http://localhost:8001"
```

### Full discover-and-match function

```python
# clientAgent/discovery.py
async def discover_and_match(query, http_client):
    for base_url in REMOTE_AGENT_URLS:
        resolver = A2ACardResolver(httpx_client=http_client, base_url=base_url)
        card = await resolver.get_agent_card()   # A2A Well-Known URI discovery
        skill = match_skill(query, card)          # tag-based skill matching
        if skill:
            return skill, card, base_url          # card carries the endpoint URL
    return None, None, None
```

---

## 7. How a User Request is Served — End to End

**Example: user types `"weather in Bangalore"`**

```
User types: "weather in Bangalore"
      │
      ▼
clientAgent/runner.py — run_agent()
      │
      │  discover_and_match("weather in Bangalore")
      │    ├─ A2ACardResolver.get_agent_card("http://localhost:8001")
      │    │    → AgentCard { name: "Weather Agent", skills: [weather_lookup] }
      │    │    → match_skill() checks tags: "weather" ✓ found
      │    └─ returns (weather_lookup skill, WeatherAgent card, "http://localhost:8001")
      │
      │  create_client(agent=card, client_config=ClientConfig(streaming=False))
      │  new_text_message("weather in Bangalore", role=ROLE_USER)
      │  client.send_message(SendMessageRequest(message=...))
      │  POST http://localhost:8001/
      │
      ▼
remoteAgents/weather/server.py
      │  DefaultRequestHandler receives the request
      │  Routes to WeatherAgentExecutor.execute()
      │
      ▼
remoteAgents/weather/agent_executor.py — execute()
      │
      │  Step 1: new_task_from_user_message(context.message)
      │          event_queue.enqueue_event(task)
      │
      │  Step 2: task_updater.update_status(TASK_STATE_WORKING)
      │          "Looking up weather data..."
      │
      │  Step 3: get_message_text(context.message) → "weather in Bangalore"
      │          _extract_city() → "Bangalore"
      │          get_weather("Bangalore") → { temp:"26°C", condition:"Cloudy", ... }
      │
      │  Step 4: _format_with_llm(query, weather_data)
      │          → "The weather in Bangalore is 26°C and Cloudy with 72% humidity."
      │          task_updater.add_artifact(parts=[new_text_part(text=formatted)])
      │
      │  Step 5: task_updater.update_status(TASK_STATE_COMPLETED)
      │
      ▼
runner.py — get_stream_response_text(response)
      │  Extracts text from the artifact in the StreamResponse
      │
      ▼
User sees: "The weather in Bangalore is 26°C and Cloudy with 72% humidity."
```

**The same flow applies to stock queries** — except the client picks the Stock Agent (port 8002) because the query contains a stock-related tag like `"aapl"` or `"stock"`.

---

## 8. Project Structure

```
a2aDemo/
│
├── main.py              ← Starts both remote agents (port 8001, 8002)
├── client_demo.py       ← CLI client: discovery → match → send → print
├── ui.py                ← Streamlit chat UI with live A2A trace panel
│
├── clientAgent/         ← Client-side A2A logic (pure SDK usage)
│   ├── discovery.py     ← A2ACardResolver + match_skill() + discover_and_match()
│   ├── runner.py        ← create_client() + send_message() + response extraction
│   └── tracer.py        ← Same as runner but yields live trace steps for the UI
│
└── remoteAgents/        ← Independent A2A agent servers
    ├── weather/
    │   ├── server.py          ← AgentCard + DefaultRequestHandler + FastAPI routes
    │   ├── agent_executor.py  ← AgentExecutor: 5-step SDK task lifecycle
    │   └── weather_tool.py    ← Mock weather data (returns temp, humidity, wind)
    └── stock/
        ├── server.py          ← AgentCard + DefaultRequestHandler + FastAPI routes
        ├── agent_executor.py  ← AgentExecutor: 5-step SDK task lifecycle
        └── stock_tool.py      ← Mock stock data (returns price, sentiment)
```

---

## 9. Sample Requests and Responses

For manual testing via Postman or curl. Send to `POST /` on the agent's port.

### Weather — port 8001

**Request:**
```json
{
  "jsonrpc": "2.0",
  "id": "req-1",
  "method": "SendMessage",
  "params": {
    "message": {
      "role": "ROLE_USER",
      "messageId": "abc123",
      "contextId": "ctx456",
      "parts": [{ "text": "What is the weather in Bangalore?" }]
    }
  }
}
```

**Response:**
```json
{
  "jsonrpc": "2.0",
  "id": "req-1",
  "result": {
    "task": {
      "status": { "state": "TASK_STATE_COMPLETED" },
      "artifacts": [
        { "name": "weather_result",
          "parts": [{ "text": "The weather in Bangalore is 26°C and Cloudy with 72% humidity and winds of 12 km/h." }] }
      ]
    }
  }
}
```

### Stock — port 8002

**Request:**
```json
{
  "jsonrpc": "2.0",
  "id": "req-2",
  "method": "SendMessage",
  "params": {
    "message": {
      "role": "ROLE_USER",
      "messageId": "def789",
      "contextId": "ctx012",
      "parts": [{ "text": "Should I buy AAPL?" }]
    }
  }
}
```

**Response:**
```json
{
  "jsonrpc": "2.0",
  "id": "req-2",
  "result": {
    "task": {
      "status": { "state": "TASK_STATE_COMPLETED" },
      "artifacts": [
        { "name": "stock_result",
          "parts": [{ "text": "AAPL is at $189.30, up $1.20 today.\nBullish — strong iPhone demand and services growth.\nGood Buy — consistent growth with solid fundamentals." }] }
      ]
    }
  }
}
```

### Available cities
`Bangalore` `Mumbai` `Delhi` `Chennai` `Hyderabad` `Kolkata` `Pune`

### Available stocks
`AAPL` `TSLA` `GOOGL` `MSFT` `AMZN` `NVDA` `META` `NFLX` `RELIANCE` `TCS` `INFY`

---

## 10. Endpoints Reference

### Weather Agent — port 8001

| Method | URL | What it does |
|---|---|---|
| GET | `/.well-known/agent-card.json` | A2A discovery — returns AgentCard with weather skills |
| POST | `/` | A2A JSON-RPC — accepts SendMessage, returns task with artifact |
| GET | `/docs` | Swagger UI for manual testing |

### Stock Agent — port 8002

| Method | URL | What it does |
|---|---|---|
| GET | `/.well-known/agent-card.json` | A2A discovery — returns AgentCard with stock skills |
| POST | `/` | A2A JSON-RPC — accepts SendMessage, returns task with artifact |
| GET | `/docs` | Swagger UI for manual testing |
