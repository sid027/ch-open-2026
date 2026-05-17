import httpx
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("Conference Research Assistant")

# ── Remote API config ──────────────────────────────────────────────────────────
# This is the ONLY change from Level 3 — interests now live on a shared server

API_BASE  = "http://34.65.167.161:5556"
API_TOKEN = "workshop-ch-open-2026"
YOUR_NAME = "participant"           # ← participants should change this to their name

HEADERS = {"Authorization": f"Bearer {API_TOKEN}"}

# ── Level 4 tools — now calling the remote API instead of local SQLite ─────────

@mcp.tool()
@mcp.tool()
def add_interest(topic: str) -> str:
    """Add a research topic to the shared group database.
    Use this tool when the user says things like:
    - 'add X to my interests'
    - 'save X as a research topic'
    - 'I am researching X'
    - 'track X for me'
    - 'put X in the list'
    Do NOT rely on memory — always call this tool to persist the topic.

    Args:
        topic: The research topic or interest to save.
    """
    try:
        response = httpx.post(
            f"{API_BASE}/interests",
            json={"topic": topic, "added_by": YOUR_NAME},
            headers=HEADERS,
            timeout=5.0,
        )
        result = response.json()
        if result.get("status") == "added":
            return f"✅ Added '{topic}' to the shared research interests."
        return f"ℹ️ '{topic}' is already in the shared interests."
    except httpx.HTTPError as e:
        return f"❌ Could not reach the shared server: {str(e)}"


@mcp.tool()
def list_interests() -> list[dict]:
    """Return all research interests saved by the whole workshop group
    from the shared remote database. Always call this tool when asked
    what topics are saved — never infer or recall from memory.
    Present the raw results to the user so they can see what is stored.
    """
    try:
        response = httpx.get(
            f"{API_BASE}/interests",
            headers=HEADERS,
            timeout=5.0,
        )
        response.raise_for_status()
        data = response.json()
        return data if data else [{"message": "No interests saved yet."}]
    except httpx.HTTPError as e:
        return [{"error": f"Could not reach the shared server: {str(e)}"}]


@mcp.tool()
def remove_interest(topic: str) -> str:
    """Remove a research interest from the shared group database.
    Use this when the user says 'remove X', 'I am no longer interested in X',
    or 'delete X from my interests'.

    Args:
        topic: The research topic to remove.
    """
    try:
        response = httpx.delete(
            f"{API_BASE}/interests/{topic}",
            headers=HEADERS,
            timeout=5.0,
        )
        if response.status_code == 200:
            return f"🗑️ Removed '{topic}' from the shared research interests."
        elif response.status_code == 404:
            return f"⚠️ '{topic}' was not found. Use list_interests to see what's saved."
        return f"❌ Unexpected response: {response.status_code}"
    except httpx.HTTPError as e:
        return f"❌ Could not reach the shared server: {str(e)}"


if __name__ == "__main__":
    mcp.run(transport="stdio")
