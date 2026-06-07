"""
A2A Protocol Client Demo — Pattern 2 (Orchestrator)

One server. Client sends any request to /a2a.
The orchestrator routes internally to the right agent.

Usage:
    python client_demo.py
"""
import asyncio
import httpx
import json

SERVER = "http://localhost:8000"


# ── Helpers ───────────────────────────────────────────────────────────────────

async def discover():
    async with httpx.AsyncClient() as client:
        r = await client.get(f"{SERVER}/.well-known/agent.json")
        return r.json()


async def send(req_id: str, text: str) -> dict:
    body = {
        "jsonrpc": "2.0",
        "id": req_id,
        "method": "message/send",
        "params": {
            "message": {
                "role": "user",
                "parts": [{"type": "text", "text": text}]
            }
        }
    }
    async with httpx.AsyncClient(timeout=45.0) as client:
        r = await client.post(f"{SERVER}/a2a", json=body)
        return r.json()


def show(label: str, query: str, result: dict):
    print(f"\n  [{label}]")
    print(f"  User  : {query}")
    if "result" in result:
        answer = result["result"]["message"]["parts"][0]["text"]
        print(f"  Agent : {answer}")
    else:
        print(f"  Error : {result.get('error', 'unknown')}")
    print()


# ── Demo ──────────────────────────────────────────────────────────────────────

async def main():
    print("\n" + "=" * 55)
    print("  A2A Protocol Demo — Orchestrator Pattern")
    print("  Single endpoint routes to the right agent")
    print("=" * 55)

    try:
        # ── Step 1: Discover ──────────────────────────────────
        print("\n  STEP 1 — Agent Discovery")
        print("  GET /.well-known/agent.json\n")
        card = await discover()
        print(f"  Agent   : {card['name']}")
        print(f"  About   : {card['description']}")
        print(f"  Skills  :")
        for s in card["skills"]:
            print(f"    - {s['name']}: {s['description']}")

        # ── Step 2: Weather queries (routed to weather_agent) ─
        print("\n" + "-" * 55)
        print("  STEP 2 — Weather Queries  -->  routed to weather_agent")
        print("-" * 55)

        weather_queries = [
            ("w-001", "What is the weather in Bangalore?"),
            ("w-002", "How is the weather in Mumbai?"),
        ]
        for req_id, q in weather_queries:
            result = await send(req_id, q)
            show("Weather", q, result)
            await asyncio.sleep(0.5)

        # ── Step 3: Stock queries (routed to stock_agent) ─────
        print("-" * 55)
        print("  STEP 3 — Stock Queries    -->  routed to stock_agent")
        print("-" * 55)

        stock_queries = [
            ("s-001", "Give me a quick analysis of AAPL"),
            ("s-002", "Should I buy TSLA?"),
        ]
        for req_id, q in stock_queries:
            result = await send(req_id, q)
            show("Stock", q, result)
            await asyncio.sleep(0.5)

        # ── Step 4: Mixed — orchestrator picks the right one ──
        print("-" * 55)
        print("  STEP 4 — Mixed Queries (orchestrator decides routing)")
        print("-" * 55)

        mixed = [
            ("m-001", "weather in Delhi"),
            ("m-002", "How is NVDA stock doing?"),
            ("m-003", "Is it sunny in Chennai?"),
            ("m-004", "Quick analysis of RELIANCE"),
        ]
        for req_id, q in mixed:
            result = await send(req_id, q)
            show("Mixed", q, result)
            await asyncio.sleep(0.5)

        print("=" * 55)
        print("  Demo complete!")
        print("=" * 55 + "\n")

    except httpx.ConnectError:
        print("\n  Could not connect. Start the server first:")
        print("  python main.py\n")


if __name__ == "__main__":
    asyncio.run(main())
