# A2A Protocol Demo — Multi-Agent Weather + Stock

A hands-on demo of Google's **[Agent-to-Agent (A2A) protocol](https://google.github.io/A2A/)** using the official **[`a2a-sdk`](https://pypi.org/project/a2a-sdk/)**. Two specialist agents run as independent HTTP servers. The **client** discovers their agent cards, matches skills, and calls the right agent directly — no orchestrator in the middle.

---

## Table of Contents

1. [What is A2A?](#1-what-is-a2a)
2. [A2A vs MCP — When to Use Which](#2-a2a-vs-mcp--when-to-use-which)
3. [About This Project](#3-about-this-project)
4. [Architecture](#4-architecture)
5. [Installation (uv)](#5-installation-uv)
6. [Project Structure](#6-project-structure)
7. [How a Request Flows](#7-how-a-request-flows)
8. [How to Run](#8-how-to-run)
9. [Sample Queries](#9-sample-queries)
10. [Endpoints Reference](#10-endpoints-reference)

---

## 1. What is A2A?

**A2A (Agent-to-Agent)** is an open protocol from Google that lets AI agents discover each other and exchange tasks over standard HTTP using JSON-RPC.

| Layer | Protocol | Connects |
|---|---|---|
| Web | HTTP | Browsers ↔ servers |
| Tools | MCP | Models ↔ tools & data sources |
| **Agents** | **A2A** | **Agents ↔ agents** |

### Core concepts

**Agent Card** — Every A2A agent publishes a machine-readable card at:

```
GET /.well-known/agent-card.json
```

The card describes the agent's name, skills, tags, supported transports, and interface URLs. Clients read it *before* sending work.

**Skills** — Declared capabilities on the card (e.g. `weather_lookup`, `stock_analysis`) with tags used for routing.

**Tasks & Messages** — Clients send a `SendMessage` JSON-RPC request. The server creates a task, processes it, and returns the result as a structured message.

**True agent boundaries** — Each agent is a separate process with its own URL. The **client** discovers agent cards, matches skills, and calls the right agent over HTTP — the standard A2A pattern.

---

## 2. A2A vs MCP — When to Use Which

Both protocols extend what LLMs can do, but they solve different problems.

| | **MCP (Model Context Protocol)** | **A2A (Agent-to-Agent)** |
|---|---|---|
| **Connects** | A model to **tools & resources** | An agent to **other agents** |
| **Unit of work** | Tool call / resource read | Task with messages & lifecycle |
| **Discovery** | Server capability list | Agent Card with skills & tags |
| **Autonomy** | Tools are passive — they execute when called | Agents are autonomous — they reason, delegate, and respond |
| **Deployment** | Usually co-located with the host app | Independent services across teams / clouds |
| **Best for** | DB queries, file access, APIs, calculators | Specialist agents owned by different teams, long-running workflows, cross-org collaboration |

### Why A2A is beneficial over MCP for agent systems

1. **Agent autonomy** — MCP tools don't think; they return data. A2A agents are full reasoning systems that can plan, use their own tools, and return finished answers.

2. **Decoupled ownership** — Weather and stock agents here run on separate ports (8001, 8002). Teams can deploy, version, and scale them independently. MCP servers are typically bundled with the host.

3. **Standard discovery** — Any A2A client can fetch an agent card and know what skills are available without custom integration code.

4. **Task lifecycle** — A2A tracks task state (`working`, `completed`, etc.), supports streaming, push notifications, and cancellation — beyond a single tool-call round trip.

5. **Composable ecosystems** — Agents from different vendors (built with ADK, LangGraph, CrewAI, etc.) can interoperate as long as they speak A2A.

> **In practice:** Use MCP when your model needs direct access to tools. Use A2A when you need agents to collaborate as peers across service boundaries. They complement each other — an A2A agent can internally use MCP tools.

---

## 3. About This Project

This demo runs **two A2A-compliant remote agents** plus a **client** that performs discovery and routing:

| Component | Port | Role |
|---|---|---|
| **Weather Agent** | 8001 | Specialist — city weather lookup + LLM formatting |
| **Stock Agent** | 8002 | Specialist — stock price lookup + LLM analysis |
| **Client** (UI / CLI) | — | Discovers agent cards, matches skill tags, calls the right agent |

There is **no orchestrator agent**. The Streamlit UI and CLI demo act as true A2A clients: they fetch `/.well-known/agent-card.json` from each remote agent, match the user's query against skill tags, and send the `SendMessage` request directly to the matched agent.

**Stack:**
- [`a2a-sdk`](https://pypi.org/project/a2a-sdk/) — official A2A protocol (server routes, client, agent card types)
- **FastAPI + Uvicorn** — HTTP servers
- **LiteLLM** — LLM formatting inside specialist agents (OpenAI GPT-3.5-turbo)

---

## 4. Architecture

```
┌─────────────────────────────────────────────────────────────┐
│  A2A Client  (Streamlit UI / CLI)                           │
│                                                             │
│  1. GET agent-card.json from :8001 and :8002  (discovery)   │
│  2. Match query tags → weather_lookup | stock_analysis      │
│  3. POST SendMessage directly to matched agent              │
└───────────────┬─────────────────────────┬───────────────────┘
                │ A2A JSON-RPC            │ A2A JSON-RPC
                ▼                         ▼
      ┌─────────────────┐     ┌─────────────────┐
      │ Weather Agent   │     │ Stock Agent     │
      │ port 8001       │     │ port 8002       │
      │ get_weather()   │     │ get_stock()     │
      │ + LLM format    │     │ + LLM format    │
      └─────────────────┘     └─────────────────┘
```

**Discovery flow (client-side routing):**

```
1. GET  /.well-known/agent-card.json  on each known agent URL
2. Read skills & tags from each card
3. Match user query → pick weather or stock agent
4. POST /  (JSON-RPC SendMessage)  directly to that agent
5. Remote agent processes task → response returned to client
```

---

## 5. Installation (uv)

[uv](https://docs.astral.sh/uv/) is a fast Python package manager. This project targets **Python 3.11+**.

### Option A — `uv sync` (recommended)

```bash
# Install uv (once)
pip install uv

# Clone / enter the project, then:
uv sync

# Create your environment file
copy .env.example .env        # Windows
# cp .env.example .env        # Mac / Linux

# Edit .env and set your OpenAI key:
# OPENAI_API_KEY=sk-your-key-here
```

`uv sync` reads `pyproject.toml`, creates `.venv`, and installs all dependencies.

### Option B — manual venv

```bash
uv venv
uv pip install -r requirements.txt
```

### Activate the virtual environment

**Windows (PowerShell):**
```powershell
.venv\Scripts\activate
```

**Mac / Linux:**
```bash
source .venv/bin/activate
```

---

## 6. Project Structure

```
a2aDemo/
│
├── main.py                         ← Starts remote A2A agents (8001, 8002)
├── client_demo.py                  ← CLI A2A client — discovery + direct routing
├── ui.py                           ← Streamlit A2A client with live trace
├── pyproject.toml                  ← Project metadata & dependencies (uv)
├── requirements.txt                ← Pip-compatible dependency list
│
├── clientAgent/                    ← A2A client layer (discovery + routing)
│   ├── discovery.py                ← Fetch agent cards, match skill tags
│   ├── runner.py                   ← Discover + call remote agent directly
│   └── tracer.py                   ← Live step-by-step trace for Streamlit
│
└── remoteAgents/                   ← Specialist A2A agents (separate processes)
    ├── weather/
    │   ├── server.py               ← Weather A2A server (port 8001)
    │   ├── agent_executor.py       ← Task handler — tool + LLM
    │   └── weather_tool.py         ← Mock weather data
    └── stock/
        ├── server.py               ← Stock A2A server (port 8002)
        ├── agent_executor.py       ← Task handler — tool + LLM
        └── stock_tool.py           ← Mock stock data
```

> **Legacy files** (not used by `main.py`): `clientAgent/server.py`, `clientAgent/agent_card.py`, and `remoteAgents/orchestrator/` contain an earlier single-server ADK prototype. The current demo uses the multi-server `a2a-sdk` architecture above.

---

## 7. How a Request Flows

Example: `"weather in Bangalore"`

```
You (UI or CLI)  — acts as A2A client
      │
      │  1. GET /.well-known/agent-card.json  (:8001, :8002)
      │  2. match_skill("weather" tag → weather_lookup on Weather card)
      │  3. POST http://localhost:8001/  (SendMessage)
      ▼
weather/server.py  ── a2a-sdk JSON-RPC handler receives the task
      │
      ▼
weather/agent_executor.py
      │  1. Extract city from message
      │  2. get_weather("Bangalore") → { temp: 26°C, ... }
      │  3. LiteLLM formats natural-language answer
      │  4. TaskUpdater.complete(message=...)
      ▼
You  ── see: "In Bangalore, the current weather is cloudy at 26°C..."
```

---

## 8. How to Run

> **Important:** Start the remote agents first. The UI and CLI are A2A *clients* — they discover agents and call them directly.

### Step 1 — Start remote A2A agents

**Terminal 1:**
```bash
python main.py
```

You should see:
```
Weather Agent                  http://localhost:8001
Stock Agent                    http://localhost:8002
```

Verify discovery:
```bash
curl http://localhost:8001/.well-known/agent-card.json
curl http://localhost:8002/.well-known/agent-card.json
```

### Option A — Streamlit UI (recommended)

**Terminal 2:**
```bash
streamlit run ui.py
```

Opens at **http://localhost:8501**

- **Trace ON** (sidebar checkbox) — two-column layout showing each A2A step live: card discovery → skill match → direct send → response
- **Trace OFF** — simple chat, client routes directly to the matched remote agent

**Try:**
- `weather in Bangalore`
- `How is the weather in Delhi?`
- `Should I buy AAPL?`
- `Give me analysis of NVDA`

### Option B — CLI client

**Terminal 2:**
```bash
python client_demo.py
```

Runs scripted queries demonstrating A2A discovery, skill matching, and multi-agent routing.

### Option C — Swagger / API docs

With servers running, open interactive docs:

| Agent | Swagger UI |
|---|---|
| Weather | http://localhost:8001/docs |
| Stock | http://localhost:8002/docs |

---

## 9. Sample Queries

The client discovers both agents, matches skill tags, and sends traffic **directly** to `http://localhost:8001` or `http://localhost:8002`. The A2A SDK handles JSON-RPC serialization.

**Weather examples:**
- `What is the weather in Bangalore?`
- `Is it raining in Mumbai?`
- `How is the weather in Chennai?`

**Stock examples:**
- `Should I buy AAPL?`
- `Give me analysis of NVDA`
- `Quick look at RELIANCE stock`

**Supported mock data:**

| Cities | Stocks |
|---|---|
| Bangalore, Mumbai, Delhi, Chennai, Hyderabad, Kolkata, Pune | AAPL, TSLA, GOOGL, MSFT, AMZN, NVDA, META, NFLX, RELIANCE, TCS, INFY |

---

## 10. Endpoints Reference

Each agent exposes the same A2A surface:

| Method | URL | Description |
|---|---|---|
| `GET` | `/.well-known/agent-card.json` | Agent discovery — skills, capabilities, transport URLs |
| `POST` | `/` | A2A JSON-RPC endpoint (`SendMessage`, `GetTask`, etc.) |
| `GET` | `/docs` | FastAPI Swagger UI |

### Agent URLs

| Agent | Base URL | Agent Card |
|---|---|---|
| Weather | http://localhost:8001 | http://localhost:8001/.well-known/agent-card.json |
| Stock | http://localhost:8002 | http://localhost:8002/.well-known/agent-card.json |

---

## Learn More

- [A2A Protocol Specification](https://google.github.io/A2A/)
- [A2A Python SDK (`a2a-sdk`)](https://pypi.org/project/a2a-sdk/)
- [Model Context Protocol (MCP)](https://modelcontextprotocol.io/)
