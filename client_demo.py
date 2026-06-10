"""
A2A Protocol Client Demo

Demonstrates true A2A client flow:
  1. Discovers remote agent cards  (A2ACardResolver → /.well-known/agent-card.json)
  2. Matches query against skill tags on each card
  3. Sends message directly to the matched agent via A2A SDK create_client
  4. Prints the response

Usage:
    python client_demo.py
    (requires remote agents running: python main.py)
"""
import asyncio

import httpx

from a2a.client import ClientConfig, ClientFactory
from a2a.client.helpers import create_text_message_object

from clientAgent.discovery import (
    discover_all_cards,
    discover_and_match,
    skill_name,
)
from clientAgent.runner import _build_message, _extract_text_from_event


# ── Helpers ───────────────────────────────────────────────────────────────────

async def send_to_agent(text: str, card, http_client: httpx.AsyncClient) -> str:
    """Send a message directly to a remote agent using ClientFactory."""
    config = ClientConfig(httpx_client=http_client, streaming=False)
    client = ClientFactory(config).create(card)

    message = _build_message(text)
    final_text = ""
    async for event in client.send_message(message):
        t = _extract_text_from_event(event)
        if t:
            final_text = t
    return final_text


def show(query: str, matched_skill, card, answer: str):
    s_name = skill_name(matched_skill) if matched_skill else "None — no match"
    agent  = card.name if card else "—"
    url    = card.url if card else "—"
    print(f"\n  Query         : {query}")
    print(f"  Skill matched : {s_name}")
    print(f"  Agent         : {agent}  ({url})")
    print(f"  Answer        : {answer}")


# ── Main ──────────────────────────────────────────────────────────────────────

async def main():
    print("\n" + "=" * 64)
    print("  A2A Client Demo — Discovery + Direct Remote Routing")
    print("=" * 64)

    try:
        async with httpx.AsyncClient(timeout=60.0) as http_client:

            # ── STEP 1: Discover all remote agent cards via A2ACardResolver ───
            print("\n  STEP 1 — A2A Discovery")
            print("  A2ACardResolver fetches /.well-known/agent-card.json\n")

            discovered = await discover_all_cards(http_client)

            for base_url, card in discovered:
                print(f"  Agent   : {card.name}  ({base_url})")
                print(f"  About   : {card.description[:80]}...")
                print(f"  Skills  :")
                for skill in card.skills:
                    tags_preview = ", ".join(skill.tags[:5])
                    print(f"    [{skill.id}]  {skill.name}")
                    print(f"      Tags    : {tags_preview}...")
                    print(f"      Examples: {skill.examples[0] if skill.examples else '—'}")
                print()

            # ── STEP 2: Skill match + direct A2A send per query ───────────────
            print("-" * 64)
            print("  STEP 2 — Skill Tag Matching + A2A Message Send\n")

            queries = [
                "What is the weather in Bangalore?",
                "Should I buy AAPL?",
                "How is the weather in Mumbai?",
                "Give me analysis of NVDA",
                "Is it sunny in Chennai?",
                "Quick look at RELIANCE stock",
            ]

            for query in queries:
                print(f"\n  {'─' * 60}")
                matched, card, base_url = await discover_and_match(query, http_client)

                if matched:
                    print(f"  Tag match : '{skill_name(matched)}'  →  {card.name} ({base_url})")
                    answer = await send_to_agent(query, card, http_client)
                else:
                    print("  No skill tag matched any remote agent card")
                    answer = "No suitable agent found. Try a weather or stock query."

                show(query, matched, card, answer)
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
