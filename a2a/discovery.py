"""
A2A Discovery — agent card skill matching.

This is real A2A protocol behaviour:
  1. Client fetches /.well-known/agent.json  (the agent card)
  2. Reads the skills list from the card
  3. Matches the user query against each skill's tags
  4. Identifies which skill (and therefore which agent) should handle the request
  5. Only then sends the message to /a2a

This replaces keyword guessing with card-driven routing awareness.
The orchestrator LLM still does the actual internal routing —
but the client/UI now knows *why* it's sending to this agent,
based on what the card advertises.
"""
import httpx


def match_skill(query: str, card: dict) -> dict | None:
    """
    Matches a user query against the skills in an agent card.

    Reads the 'tags' list of each skill and checks if any tag
    appears in the query (case-insensitive). Returns the first
    matching skill dict, or None if no match found.

    Args:
        query: The user's message text.
        card:  The agent card dict from /.well-known/agent.json

    Returns:
        The matching skill dict  e.g. { "id": "weather_lookup", "name": ..., "tags": [...] }
        or None if no skill matches.
    """
    query_lower = query.lower()
    for skill in card.get("skills", []):
        for tag in skill.get("tags", []):
            if tag.lower() in query_lower:
                return skill
    return None


async def fetch_card(base_url: str) -> dict:
    """
    Fetches the agent card from /.well-known/agent.json.

    Args:
        base_url: e.g. "http://localhost:8000"

    Returns:
        The agent card as a dict.
    """
    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.get(f"{base_url}/.well-known/agent.json")
        response.raise_for_status()
        return response.json()


def skill_to_agent(skill: dict | None) -> str:
    """
    Maps a matched skill id to the specialist agent name.
    Returns 'unknown' if skill is None.
    """
    if skill is None:
        return "unknown"
    mapping = {
        "weather_lookup": "weather_agent",
        "stock_analysis":  "stock_agent",
    }
    return mapping.get(skill["id"], "unknown")
