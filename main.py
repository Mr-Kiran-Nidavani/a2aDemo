"""
A2A Demo — Entry point
One server. One endpoint. Orchestrator routes internally.

Run: python main.py
"""
import uvicorn


def main():
    print("=" * 55)
    print("  A2A Multi-Agent Demo")
    print("=" * 55)
    print()
    print("  One server, two specialist agents:")
    print("  - Weather Agent  (city weather questions)")
    print("  - Stock Agent    (stock price + analysis)")
    print()
    print("  Endpoints:")
    print("  Agent card : http://localhost:8000/.well-known/agent.json")
    print("  Health     : http://localhost:8000/health")
    print("  A2A        : http://localhost:8000/a2a")
    print("  Docs       : http://localhost:8000/docs")
    print()
    print("  Run client in another terminal:")
    print("  python client_demo.py")
    print("=" * 55)

    uvicorn.run("a2a.server:app", host="0.0.0.0", port=8000, reload=True)


if __name__ == "__main__":
    main()
