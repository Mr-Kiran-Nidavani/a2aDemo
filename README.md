# A2A Protocol Demo — Weather + Stock Agents

---

## Table of Contents

1. [What is A2A?](#1-what-is-a2a)
2. [How A2A Works](#2-how-a2a-works)
3. [About This Project](#3-about-this-project)
4. [Installation](#4-installation)
5. [Project Structure](#5-project-structure)
6. [How a Request Flows Through the Code](#6-how-a-request-flows-through-the-code)
7. [Code Snippets — How the Pieces Connect](#7-code-snippets--how-the-pieces-connect)
8. [How to Run](#8-how-to-run)
   - [Option A — Streamlit UI](#option-a--streamlit-ui-recommended)
   - [Option B — CLI Client](#option-b--cli-client)
   - [Option C — API Docs / Postman](#option-c--api-docs--postman)
9. [Sample Requests and Responses](#9-sample-requests-and-responses)
10. [Endpoints Reference](#10-endpoints-reference)

---

## 1. What is A2A?

**A2A (Agent-to-Agent)** is a protocol that lets AI agents talk to each other over HTTP using a standard message format (JSON-RPC).

Think of it like this:

| Protocol | Used for |
|---|---|
| HTTP | Web browsers talking to servers |
| MCP | AI models talking to tools |
| **A2A** | **AI agents talking to other AI agents** |

One agent sends a message. Another receives it, processes it, and sends back a response. Neither agent needs to know how the other is built internally.

---

## 2. How A2A Works

```
Agent A (client)                    Agent B (server)
      │                                   │
      │  1. GET /.well-known/agent.json   │
      │ ─────────────────────────────────►│  "What can you do?"
      │◄─────────────────────────────────│  Returns agent card (skills, capabilities)
      │                                   │
      │  2. POST /a2a  (JSON-RPC)         │
      │ ─────────────────────────────────►│  "weather in Bangalore"
      │◄─────────────────────────────────│  "26°C, Cloudy"
      │                                   │
```

Every A2A message follows this shape:

```json
{
  "jsonrpc": "2.0",
  "id": "1",
  "method": "message/send",
  "params": {
    "message": {
      "role": "user",
      "parts": [{ "type": "text", "text": "your question here" }]
    }
  }
}
```

---

## 3. About This Project

This project runs **one server** with **two specialist agents** behind an **orchestrator**.

- You send any message to a single endpoint
- The orchestrator reads your message and decides which agent should handle it
- The right agent answers — you never talk to the specialist agents directly

```
You ──► Orchestrator ──► Weather Agent  (city weather questions)
                    └──► Stock Agent    (stock price + analysis)
```

Agents are built with **Google ADK** and exposed over the **A2A protocol** via **FastAPI**.

---

## 4. Installation

### Step 1 — Install uv

uv is a fast Python package manager. Install it once on your machine.

```bash
pip install uv
```

> Already have uv? Skip to Step 2.

---

### Step 2 — Create a virtual environment

```bash
uv venv
```

Creates a `.venv` folder — an isolated Python environment so packages don't conflict with other projects.

---

### Step 3 — Activate the virtual environment

**Windows:**
```bash
.venv\Scripts\activate
```

**Mac / Linux:**
```bash
source .venv/bin/activate
```

Your terminal prompt will show `(.venv)` when active.

---

### Step 4 — Install dependencies

```bash
uv pip install -r requirements.txt
```

Installs FastAPI, Google ADK, LiteLLM, Streamlit, and everything else the project needs.

---

### Step 5 — Add your API key

Open the `.env` file and set your OpenAI key:

```
OPENAI_API_KEY=sk-your-key-here
```

---

## 5. Project Structure

```
a2aDemo/
│
├── main.py                ← Starts the A2A server on port 8000
├── client_demo.py         ← CLI client — discovers agent card, matches skills, sends requests
├── ui.py                  ← Streamlit chat UI with live request trace
│
├── a2a/                   ← A2A protocol layer (HTTP-facing)
│   ├── agent_card.py      ← Agent's "business card" — name, skills, tags, capabilities
│   ├── discovery.py       ← Reads agent card, matches query to skill, identifies routing
│   ├── server.py          ← FastAPI server — receives and validates HTTP requests
│   ├── runner.py          ← Pure ADK execution — creates session, runs agent, returns text
│   └── tracer.py          ← Wraps runner with live trace steps for the Streamlit UI
│
└── agents/                ← The actual AI agents
    ├── orchestrator/
    │   └── agent.py       ← Receives message, delegates to the right specialist via AgentTool
    ├── weather/
    │   ├── agent.py       ← Weather LLM agent
    │   └── weather_tool.py   ← Returns weather data for a city
    └── stock/
        ├── agent.py       ← Stock LLM agent
        └── stock_tool.py     ← Returns stock price and sentiment
```

---

## 6. How a Request Flows Through the Code

What happens when you send `"weather in Bangalore"`:

```
You (UI or client)
      │
      │  POST /a2a
      │  { "method": "message/send", "text": "weather in Bangalore" }
      ▼
server.py  ── validates the JSON-RPC shape, extracts the text
      │
      ▼
runner.py  ── creates an ADK session, feeds the message to the orchestrator
      │
      ▼
orchestrator/agent.py  ── LLM reads the message, picks weather_agent
      │
      ▼
weather/agent.py  ── LLM decides to call the get_weather tool
      │
      ▼
weather/weather_tool.py  ── returns { temp: "26°C", condition: "Cloudy", ... }
      │
      ▼
weather/agent.py  ── LLM formats: "It is 26°C and Cloudy in Bangalore..."
      │
      ▼
runner.py  ── captures the final response
      │
      ▼
server.py  ── wraps it in A2A JSON-RPC response format
      │
      ▼
You  ── see the answer
```

---

## 7. Code Snippets — How the Pieces Connect

### 1. The Tool — raw data lookup

Just a plain Python function. No AI — just a lookup.

```python
# agents/weather/weather_tool.py
def get_weather(city: str) -> dict:
    weather_data = {
        "bangalore": {"temperature": "26°C", "condition": "Cloudy", ...},
        "mumbai":    {"temperature": "31°C", "condition": "Humid",  ...},
    }
    return weather_data.get(city.lower(), {"status": "not_found"})
```

---

### 2. The Specialist Agent — LLM + tool

The agent is an LLM that knows about the tool. It calls `get_weather` and formats the answer.

```python
# agents/weather/agent.py
root_agent = Agent(
    name="weather_agent",
    instruction="Answer weather questions using the get_weather tool.",
    tools=[get_weather]   # ← tool attached here
)
```

Same pattern for stock:

```python
# agents/stock/agent.py
root_agent = Agent(
    name="stock_agent",
    instruction="Respond in 3 lines: price, sentiment, verdict.",
    tools=[get_stock]
)
```

---

### 3. The Orchestrator — routing logic

Wraps both specialist agents as `AgentTool`. Reads intent and delegates.

```python
# agents/orchestrator/agent.py
orchestrator = Agent(
    name="orchestrator",
    instruction="""
        If weather question → delegate to weather_agent
        If stock question   → delegate to stock_agent
        Never answer yourself. Always delegate.
    """,
    tools=[
        AgentTool(agent=weather_agent),  # ← weather agent as a callable
        AgentTool(agent=stock_agent),    # ← stock agent as a callable
    ]
)
```

---

### 4. The Runner — ADK bridge

Takes plain text, runs it through the orchestrator, returns the final answer.

```python
# a2a/runner.py
async def run_agent(user_message: str) -> str:
    session_id = str(uuid.uuid4())   # fresh session every time

    async for event in runner.run_async(...):
        if event.is_final_response():  # skip tool calls, take only the final answer
            final_response = event.content.parts[0].text
            break

    return final_response
```

---

### 5. The Server — A2A HTTP layer

Receives JSON-RPC, calls the runner, wraps the result back in JSON-RPC.

```python
# a2a/server.py
@app.post("/a2a")
async def a2a_endpoint(body: A2ARequest):
    user_text = body.params.message.parts[0].text  # extract the message
    result = await run_agent(user_text)             # run through orchestrator

    return {
        "jsonrpc": "2.0",
        "id": body.id,
        "result": {
            "status": "completed",
            "message": {"role": "agent", "parts": [{"type": "text", "text": result}]}
        }
    }
```

---

### 6. The Agent Card — discovery

Any client can ask "what can you do?" before sending a message.

```python
# a2a/agent_card.py
AGENT_CARD = {
    "name": "orchestrator",
    "skills": [
        { "id": "weather_lookup", "name": "Weather Lookup" },
        { "id": "stock_analysis", "name": "Stock Analysis" }
    ]
}

# a2a/server.py
@app.get("/.well-known/agent.json")
async def agent_card():
    return AGENT_CARD   # ← any agent or client can discover capabilities here
```

---

## 8. How to Run

---

### Option A — Streamlit UI (recommended)

The UI includes a chat window and an optional **live request trace panel**. Use the **"Show request trace"** checkbox in the sidebar to switch between modes.

**No need to start the server separately. Just run:**

```bash
streamlit run ui.py
```

Opens at **http://localhost:8501**

**Trace ON** (default) — two-column layout, shows each step live:

```
┌──────────────────────┬──────────────────────────────────┐
│  Chat                │  Live Request Flow               │
│                      │                                  │
│  You: weather in     │  Step 1  Agent Card read         │
│       Bangalore      │          Skills: Weather, Stock  │
│                      │                                  │
│  Agent: 26°C,        │  Step 2  Skill matched: Weather  │
│  Cloudy in           │          Tag: "weather"          │
│  Bangalore...        │                                  │
│                      │  Step 3  A2A Request sent        │
│  > type here...      │          POST /a2a               │
│                      │                                  │
│                      │  Step 4  Orchestrator thinking   │
│                      │                                  │
│                      │  Step 5  Tool called:            │
│                      │          get_weather("bangalore")│
│                      │                                  │
│                      │  Step 6  Tool response           │
│                      │          { temp: 26°C, ... }     │
│                      │                                  │
│                      │  Step 7  A2A Response returned   │
└──────────────────────┴──────────────────────────────────┘
```

**Trace OFF** — single-column chat only, calls `run_agent()` directly with no trace overhead. Faster, cleaner.

Try these queries in the chat:
- `weather in Bangalore`
- `How is the weather in Delhi?`
- `Should I buy AAPL?`
- `Give me analysis of NVDA`

---

### Option B — CLI Client

Runs a scripted demo from the terminal. Tests weather queries, stock queries, and mixed queries automatically.

**Terminal 1 — start the server:**
```bash
python main.py
```

**Terminal 2 — run the client:**
```bash
python client_demo.py
```

The client will:
1. Discover the agent via `/.well-known/agent.json`
2. Send weather queries → prints request + response
3. Send stock queries → prints request + response
4. Send mixed queries → orchestrator decides routing

---

### Option C — API Docs / Postman

Start the server and open the interactive Swagger UI in your browser.

```bash
python main.py
```

Then open: **http://localhost:8000/docs**

You can try all endpoints directly in the browser — no extra tools needed. Use the `/a2a` POST endpoint with the sample JSON from the next section.

---

## 9. Sample Requests and Responses

All requests go to `POST http://localhost:8000/a2a`

---

### Weather query

**Request:**
```json
{
  "jsonrpc": "2.0",
  "id": "1",
  "method": "message/send",
  "params": {
    "message": {
      "role": "user",
      "parts": [{ "type": "text", "text": "What is the weather in Bangalore?" }]
    }
  }
}
```

**Response:**
```json
{
  "jsonrpc": "2.0",
  "id": "1",
  "result": {
    "status": "completed",
    "message": {
      "role": "agent",
      "parts": [{ "type": "text", "text": "The weather in Bangalore is 26°C and Cloudy with 72% humidity." }]
    }
  }
}
```

---

### Stock query

**Request:**
```json
{
  "jsonrpc": "2.0",
  "id": "2",
  "method": "message/send",
  "params": {
    "message": {
      "role": "user",
      "parts": [{ "type": "text", "text": "Should I buy AAPL?" }]
    }
  }
}
```

**Response:**
```json
{
  "jsonrpc": "2.0",
  "id": "2",
  "result": {
    "status": "completed",
    "message": {
      "role": "agent",
      "parts": [{ "type": "text", "text": "AAPL is at $189.30, up $1.20 today.\nBullish — strong iPhone demand and services growth.\nGood Buy — consistent growth with solid fundamentals." }]
    }
  }
}
```

---

### Available cities
`Bangalore` `Mumbai` `Delhi` `Chennai` `Hyderabad` `Kolkata` `Pune`

### Available stocks
`AAPL` `TSLA` `GOOGL` `MSFT` `AMZN` `NVDA` `META` `NFLX` `RELIANCE` `TCS` `INFY`

---

## 10. Endpoints Reference

| Method | URL | What it does |
|---|---|---|
| GET | `/.well-known/agent.json` | Agent discovery — returns name, skills, capabilities |
| GET | `/health` | Check if server is running, shows active agents |
| POST | `/a2a` | Send a message, get a response |
| GET | `/docs` | Interactive Swagger UI — try endpoints in browser |
