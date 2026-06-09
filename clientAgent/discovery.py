"""
A2A Discovery — agent card resolution and skill matching.

Official A2A discovery pattern (Well-Known URI strategy):
  1. Client knows remote agent base URLs (config / env vars)
  2. A2ACardResolver fetches /.well-known/agent-card.json from each
  3. Client reads AgentSkill.tags from each card
  4. Matches the user query against tags (case-insensitive)
  5. Routes to the matched agent's URL from AgentCard.supported_interfaces

No hardcoded skill→URL mappings — the agent card itself is the source of truth.
"""
import httpx
from a2a.client import A2ACardResolver

# Known remote agent base URLs.
# In production these come from a registry, DNS, or environment config.
REMOTE_AGENT_URLS = [
    "http://localhost:8001",  # Weather Agent
    "http://localhost:8002",  # Stock Agent
]


# ── Skill matching ────────────────────────────────────────────────────────────

def match_skill(query: str, card) -> object | None:
    """
    Matches a user query against the skill tags on an AgentCard.

    Iterates over card.skills, checks each skill's tags list.
    Returns the first AgentSkill whose tag appears in the query, or None.
    """
    query_lower = query.lower()
    for skill in (card.skills or []):
        for tag in (skill.tags or []):
            if tag.lower() in query_lower:
                return skill
    return None


# ── Convenience accessors ─────────────────────────────────────────────────────

def skill_name(skill) -> str:
    return skill.name if skill else "Unknown"


def skill_id(skill) -> str:
    return skill.id if skill else ""


def card_name(card) -> str:
    return card.name if card else "Unknown"


def card_url(card) -> str:
    """Returns the first interface URL from the agent card — no hardcoding needed."""
    if card and card.supported_interfaces:
        return card.supported_interfaces[0].url
    return ""


# ── Discovery functions ───────────────────────────────────────────────────────

async def discover_all_cards(
    http_client: httpx.AsyncClient,
) -> list[tuple[str, object]]:
    """
    Fetches AgentCards from all known remote agents using A2ACardResolver.

    This is the official A2A Well-Known URI discovery:
      GET {base_url}/.well-known/agent-card.json

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
    Iterates over known remote agents, fetches their AgentCards via
    A2ACardResolver, and returns the first card whose skill tags match the query.

    Returns:
        (matched_skill, AgentCard, base_url)  or  (None, None, None)
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
