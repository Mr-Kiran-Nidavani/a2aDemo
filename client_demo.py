"""
A2A Protocol Client Demo — Orchestrator Pattern

Demonstrates true A2A flow:
  1. Client fetches agent card  (discovery)
  2. Matches query against card skills  (capability check)
  3. Sends message only if a skill matches
  4. Prints the A2A response

Usage:
    python client_demo.py
    (requires server running: python main.py)
"""
import asyncio
import httpx
import json

from a2a.discovery import fetch_card, match_skill, skill_to_agent

SERVER = "http://localhost:8000"


# ── Helpers ───────────────────────────────────────────────────────────────────

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


def show(query: str, matched_skill: dict | None, result: dict):
    skill_name = matched_skill["name"] if matched_skill else "Unknown — LLM decides"
    agent_name = skill_to_agent(matched_skill)
    print(f"\n  Query         : {query}")
    print(f"  Skill matched : {skill_name}")
    print(f"  Routes to     : {agent_name}")
    if "result" in result:
        answer = result["result"]["message"]["parts"][0]["text"]
        print(f"  Answer        : {answer}")
    else:
        print(f"  Error         : {result.get('error', 'unknown')}")


# ── Main ──────────────────────────────────────────────────────────────────────

async def main():
    print("\n" + "=" * 60)
    print("  A2A Client Demo — True Discovery + Routing")
    print("=" * 60)

    try:
        # ── STEP 1: Fetch agent card (A2A Discovery) ──────────────────────────
        print("\n  STEP 1 — A2A Discovery")
        print(f"  GET {SERVER}/.well-known/agent.json\n")

        card = await fetch_card(SERVER)

        print(f"  Agent   : {card['name']}")
        print(f"  About   : {card['description']}")
        print(f"  Skills  :")
        for s in card["skills"]:
            print(f"    [{s['id']}]  {s['name']}")
            print(f"      Tags : {', '.join(s['tags'][:6])}...")

        # ── STEP 2: Match queries against card skills ─────────────────────────
        print("\n" + "-" * 60)
        print("  STEP 2 — Skill Matching + Message Send")
        print("  (client reads card skills, matches tags, then sends)\n")

        queries = [
            ("q-001", "What is the weather in Bangalore?"),
            ("q-002", "Should I buy AAPL?"),
            ("q-003", "How is the weather in Mumbai?"),
            ("q-004", "Give me analysis of NVDA"),
            ("q-005", "Is it sunny in Chennai?"),
            ("q-006", "Quick look at RELIANCE stock"),
        ]

        for req_id, query in queries:
            print(f"\n  {'─' * 56}")

            # Match against agent card — this is the real A2A discovery step
            matched = match_skill(query, card)

            if matched:
                print(f"  Card match found: '{matched['name']}'")
                result = await send(req_id, query)
                show(query, matched, result)
            else:
                print(f"  No card match — sending anyway, orchestrator will decide")
                result = await send(req_id, query)
                show(query, None, result)

            await asyncio.sleep(0.5)

        print("\n" + "=" * 60)
        print("  Demo complete!")
        print("=" * 60 + "\n")

    except httpx.ConnectError:
        print("\n  Could not connect. Start the server first:")
        print("  python main.py\n")


if __name__ == "__main__":
    asyncio.run(main())
