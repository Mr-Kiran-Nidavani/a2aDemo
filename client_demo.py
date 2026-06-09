"""
A2A Protocol Client Demo

Demonstrates true A2A client flow (no orchestrator):
  1. Discovers remote agent cards  (/.well-known/agent-card.json)
  2. Matches query against skill tags on each card
  3. Sends message directly to the matched agent via A2A SDK Client
  4. Prints the response

Usage:
    python client_demo.py
    (requires remote agents running: python main.py)
"""
import asyncio

import httpx

from a2a.client.client_factory import ClientConfig, ClientFactory

from clientAgent.discovery import (
    card_name,
    discover_all_cards,
    discover_and_match,
    skill_name,
    skill_to_agent,
)
from clientAgent.runner import _build_request, _extract_text


# ── Helpers ───────────────────────────────────────────────────────────────────

async def send_to_agent(text: str, card, http_client: httpx.AsyncClient) -> str:
    """Send a message directly to a remote agent using the A2A SDK Client."""
    factory = ClientFactory(ClientConfig(httpx_client=http_client, streaming=False))
    client = factory.create(card)
    request = _build_request(text)

    final_text = ""
    async for response in client.send_message(request):
        t = _extract_text(response)
        if t:
            final_text = t
    return final_text


def show(query: str, matched_skill, base_url: str | None, answer: str):
    skill_label = skill_name(matched_skill) if matched_skill else "None"
    agent_name = skill_to_agent(matched_skill) if matched_skill else "—"
    print(f"\n  Query         : {query}")
    print(f"  Skill matched : {skill_label}")
    print(f"  Agent URL     : {base_url or '—'}")
    print(f"  Routes to     : {agent_name}")
    print(f"  Answer        : {answer}")


# ── Main ──────────────────────────────────────────────────────────────────────

async def main():
    print("\n" + "=" * 64)
    print("  A2A Client Demo — Discovery + Direct Remote Routing")
    print("=" * 64)

    try:
        async with httpx.AsyncClient(timeout=60.0) as http_client:

            # ── STEP 1: Discover all remote agent cards ───────────────────────
            print(f"\n  STEP 1 — A2A Discovery (remote agents)\n")

            discovered = await discover_all_cards(http_client)
            for base_url, card_dict in discovered:
                print(f"  GET {base_url}/.well-known/agent-card.json")
                print(f"  Agent   : {card_dict.get('name', '?')}")
                print(f"  About   : {card_dict.get('description', '')[:80]}...")
                print(f"  Skills  :")
                for s in card_dict.get("skills", []):
                    print(f"    [{s['id']}]  {s['name']}")
                    print(f"      Tags : {', '.join(s['tags'][:6])}...")
                print()

            # ── STEP 2: Skill match + direct send per query ───────────────────
            print("-" * 64)
            print("  STEP 2 — Skill Matching + Direct A2A Message Send")
            print("  (client matches tags, calls the right remote agent)\n")

            queries = [
                "What is the weather in Bangalore?",
                "Should I buy AAPL?",
                "How is the weather in Mumbai?",
                "Give me analysis of NVDA",
                "Is it sunny in Chennai?",
                "Quick look at RELIANCE stock",
            ]

            for query in queries:
                print(f"\n  {'-' * 60}")
                matched, card, base_url = await discover_and_match(query, http_client)

                if matched:
                    print(
                        f"  Card match: '{skill_name(matched)}' on "
                        f"{card_name(card)}  ->  sending via A2A SDK"
                    )
                    answer = await send_to_agent(query, card, http_client)
                else:
                    print("  No skill match on any remote agent card")
                    answer = (
                        "I could not find a suitable agent for your request. "
                        "Try asking about weather in a city or a stock analysis."
                    )

                show(query, matched, base_url, answer)
                await asyncio.sleep(0.5)

        print("\n" + "=" * 64)
        print("  Demo complete!")
        print("=" * 64 + "\n")

    except httpx.ConnectError:
        print("\n  Could not connect. Start remote agents first:")
        print("  python main.py\n")
    except Exception as e:
        print(f"\n  Error: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(main())
