"""
A2A Discovery — agent card skill matching and remote agent resolution.

True A2A client behaviour (no orchestrator in the middle):
  1. Client fetches /.well-known/agent-card.json from each known remote agent
  2. Reads the skills list on each card
  3. Matches the user query against each skill's tags
  4. Sends the message directly to the matched agent's JSON-RPC endpoint
"""
import httpx

from a2a.client.card_resolver import A2ACardResolver

# Known remote agents in this demo (in production: registry, DNS, or agent directory)
REMOTE_AGENT_URLS = [
    "http://localhost:8001",  # Weather Agent
    "http://localhost:8002",  # Stock Agent
]


def match_skill(query: str, card) -> object | None:
    """
    Matches a user query against the skills in an agent card.

    Reads the 'tags' list of each skill and checks if any tag
    appears in the query (case-insensitive). Returns the first
    matching skill object (or dict), or None if no match found.

    Works with both AgentCard SDK objects and plain dicts.
    """
    query_lower = query.lower()

    if hasattr(card, "skills"):
        skills = card.skills or []
    else:
        skills = card.get("skills", [])

    for skill in skills:
        if hasattr(skill, "tags"):
            tags = skill.tags or []
        else:
            tags = skill.get("tags", [])

        for tag in tags:
            if tag.lower() in query_lower:
                return skill

    return None


def skill_name(skill) -> str:
    if skill is None:
        return "Unknown"
    return skill.name if hasattr(skill, "name") else skill.get("name", "Unknown")


def skill_id(skill) -> str:
    if skill is None:
        return ""
    return skill.id if hasattr(skill, "id") else skill.get("id", "")


def card_name(card) -> str:
    if card is None:
        return "Unknown"
    return card.name if hasattr(card, "name") else card.get("name", "Unknown")


async def fetch_card_dict(base_url: str) -> dict:
    """
    Fetches the agent card from /.well-known/agent-card.json as a plain dict.

    NOTE: This is NOT the recommended A2A discovery approach.
    The official way is A2ACardResolver (see discover_and_match below).
    This helper is kept only for display formatting in the tracer UI.
    """
    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.get(f"{base_url}/.well-known/agent-card.json")
        response.raise_for_status()
        return response.json()


async def discover_all_cards(
    http_client: httpx.AsyncClient,
) -> list[tuple[str, object]]:
    """
    Fetches agent cards from all known remote agents using A2ACardResolver.
    This is the correct A2A discovery pattern — uses the SDK resolver,
    not raw HTTP fetches.

    Returns:
        List of (base_url, AgentCard) for reachable agents.
    """
    discovered = []
    for base_url in REMOTE_AGENT_URLS:
        try:
            resolver = A2ACardResolver(httpx_client=http_client, base_url=base_url)
            card = await resolver.get_agent_card()
            discovered.append((base_url, card))
        except Exception:
            continue
    return discovered


async def discover_and_match(
    query: str,
    http_client: httpx.AsyncClient,
) -> tuple[object | None, object | None, str | None]:
    """
    Discovers remote agents and returns the first card whose skills match the query.

    Returns:
        (matched_skill, agent_card, base_url) or (None, None, None)
    """
    for base_url in REMOTE_AGENT_URLS:
        try:
            resolver = A2ACardResolver(httpx_client=http_client, base_url=base_url)
            card = await resolver.get_agent_card()
            skill = match_skill(query, card)
            if skill is not None:
                return skill, card, base_url
        except Exception:
            continue

    return None, None, None


# Backward-compatible alias (kept for client_demo.py display only)
fetch_card = fetch_card_dict

def skill_to_agent_url(skill) -> str:
    skill_id_val = skill_id(skill)
    mapping = {
        "weather_lookup": "http://localhost:8001",
        "stock_analysis": "http://localhost:8002",
    }
    return mapping.get(skill_id_val, REMOTE_AGENT_URLS[0])


def skill_to_agent(skill) -> str:
    skill_id_val = skill_id(skill)
    mapping = {
        "weather_lookup": "weather_agent",
        "stock_analysis": "stock_agent",
    }
    return mapping.get(skill_id_val, "unknown")
