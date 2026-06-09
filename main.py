"""
A2A Demo — Entry point

Starts the two remote A2A specialist agents:
  - Weather Agent   http://localhost:8001
  - Stock Agent     http://localhost:8002

The client (UI / CLI) discovers these agents via agent cards and routes
directly to the right one based on skill tags — no orchestrator in between.

Run:
    python main.py

Then in another terminal:
    python client_demo.py        # CLI demo
    streamlit run ui.py          # Streamlit UI
"""
import asyncio
import uvicorn


SERVERS = [
    {
        "app": "remoteAgents.weather.server:app",
        "host": "0.0.0.0",
        "port": 8001,
        "label": "Weather Agent",
    },
    {
        "app": "remoteAgents.stock.server:app",
        "host": "0.0.0.0",
        "port": 8002,
        "label": "Stock Agent",
    },
]


async def serve(config: dict) -> None:
    """Start a single uvicorn server asynchronously."""
    cfg = uvicorn.Config(
        app=config["app"],
        host=config["host"],
        port=config["port"],
        log_level="info",
    )
    server = uvicorn.Server(cfg)
    await server.serve()


async def main() -> None:
    print("=" * 60)
    print("  A2A Multi-Agent Demo — True A2A SDK Protocol")
    print("=" * 60)
    print()
    for s in SERVERS:
        print(f"  {s['label']:<30} http://localhost:{s['port']}")
    print()
    print("  Agent cards:")
    print("  http://localhost:8001/.well-known/agent-card.json  (weather)")
    print("  http://localhost:8002/.well-known/agent-card.json  (stock)")
    print()
    print("  Docs (Swagger):")
    for s in SERVERS:
        print(f"  http://localhost:{s['port']}/docs")
    print()
    print("  Client discovers agents and routes by skill — no orchestrator.")
    print("  Run client in another terminal:")
    print("  python client_demo.py")
    print("  streamlit run ui.py")
    print("=" * 60)

    await asyncio.gather(*[serve(s) for s in SERVERS])


if __name__ == "__main__":
    asyncio.run(main())
