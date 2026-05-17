"""
Level 5 BAD — conference_assistant_bad_server.py
One tool per filter field. Shown first so participants feel the pain.
"""
import httpx
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("Conference Assistant — Bad Design")

OPENALEX_URL = "https://api.openalex.org/works"
ARXIV_API    = "https://export.arxiv.org/api/query"
API_BASE     = "http://34.65.167.161:5556"
API_TOKEN    = "workshop-ch-open-2026"
YOUR_NAME    = "participant"   # ← change to your name
HEADERS      = {"Authorization": f"Bearer {API_TOKEN}"}
MAILTO       = "your email"  # ← optional but gives higher rate limits


def _fetch_conference_papers(extra_filters: str = "", query: str = "") -> list[dict]:
    """Shared helper — fetches conference proceedings from OpenAlex."""
    params = {
        "filter":  f"type:article,primary_location.source.type:conference{(',' + extra_filters) if extra_filters else ''}",
        "sort":    "publication_date:desc",
        "per_page": 10,
        "mailto":  MAILTO,
    }
    if query:
        params["search"] = query
    try:
        r = httpx.get(OPENALEX_URL, params=params, timeout=10.0)
        r.raise_for_status()
        results = r.json().get("results", [])
        return [
            {
                "title":       w.get("title", ""),
                "year":        w.get("publication_year", ""),
                "venue":       ((w.get("primary_location") or {}).get("source") or {}).get("display_name", ""),
                "open_access": (w.get("open_access") or {}).get("is_oa", False),
                "cited_by":    w.get("cited_by_count", 0),
                "doi":         w.get("doi", ""),
            }
            for w in results
        ]
    except httpx.HTTPError as e:
        return [{"error": str(e)}]


# BAD: one tool per filter — forces multiple tool calls for one question
@mcp.tool()
def search_conferences_by_topic(topic: str) -> list[dict]:
    """Search conference papers by topic keyword only."""
    return _fetch_conference_papers(query=topic)


@mcp.tool()
def search_conferences_by_year(year: int) -> list[dict]:
    """Search conference papers by publication year only."""
    return _fetch_conference_papers(extra_filters=f"publication_year:{year}")


@mcp.tool()
def search_conferences_open_access_only() -> list[dict]:
    """Search for open access conference papers only."""
    return _fetch_conference_papers(extra_filters="open_access.is_oa:true")


@mcp.tool()
def search_conferences_highly_cited(min_citations: int = 50) -> list[dict]:
    """Search for highly cited conference papers only."""
    return _fetch_conference_papers(extra_filters=f"cited_by_count:>{min_citations}")


@mcp.tool()
def list_recent_conference_papers() -> list[dict]:
    """List the most recent conference papers with no filters."""
    return _fetch_conference_papers()


# ── Carried-over tools ─────────────────────────────────────────────────────────

@mcp.tool()
def search_research_papers(topic: str, max_results: int = 5) -> list[dict]:
    """Search arXiv (arxiv.org) for academic papers and preprints.
    ONLY use this tool — do NOT use web search — when the user asks
    about papers, research, studies, or publications on any topic.

    Args:
        topic: The research topic or keywords to search for.
        max_results: Number of results to return (default 5, max 20).
    """
    max_results = min(max_results, 20)
    params = {
        "search_query": f"all:{topic}", "start": 0,
        "max_results": max_results, "sortBy": "submittedDate", "sortOrder": "descending",
    }
    try:
        r = httpx.get(ARXIV_API, params=params, timeout=10.0)
        r.raise_for_status()
    except httpx.HTTPError as e:
        return [{"error": f"Failed to reach arXiv: {str(e)}"}]
    import xml.etree.ElementTree as ET
    ns = {"atom": "http://www.w3.org/2005/Atom"}
    root = ET.fromstring(r.text)
    papers = []
    for entry in root.findall("atom:entry", ns):
        title     = entry.findtext("atom:title", default="", namespaces=ns).strip().replace("\n", " ")
        summary   = entry.findtext("atom:summary", default="", namespaces=ns).strip().replace("\n", " ")
        published = entry.findtext("atom:published", default="", namespaces=ns)[:10]
        link_el   = entry.find("atom:link[@rel='alternate']", ns)
        url       = link_el.attrib.get("href", "") if link_el is not None else ""
        authors   = [a.findtext("atom:name", default="", namespaces=ns) for a in entry.findall("atom:author", ns)]
        papers.append({"title": title, "authors": authors[:3], "published": published,
                       "summary": summary[:300] + "…" if len(summary) > 300 else summary, "url": url})
    return papers or [{"message": f"No papers found for: '{topic}'"}]


@mcp.tool()
def add_interest(topic: str) -> str:
    """Add a research topic to the shared group database.
    Use this when the user says: 'add X to my interests', 'save X as a research topic',
    'I am researching X, track it', or 'put X in the list'.

    Args:
        topic: The research topic or interest to save.
    """
    try:
        r = httpx.post(f"{API_BASE}/interests", json={"topic": topic, "added_by": YOUR_NAME},
                       headers=HEADERS, timeout=5.0)
        result = r.json()
        return f"Added '{topic}'." if result.get("status") == "added" else f"'{topic}' already exists."
    except httpx.HTTPError as e:
        return f"Could not reach the shared server: {str(e)}"


@mcp.tool()
def list_interests() -> list[dict]:
    """Return all research interests saved by the whole workshop group.
    Always call this tool when asked what topics are saved — never infer from memory.
    """
    try:
        r = httpx.get(f"{API_BASE}/interests", headers=HEADERS, timeout=5.0)
        r.raise_for_status()
        data = r.json()
        return data if data else [{"message": "No interests saved yet."}]
    except httpx.HTTPError as e:
        return [{"error": f"Could not reach the shared server: {str(e)}"}]


@mcp.tool()
def remove_interest(topic: str) -> str:
    """Remove a research interest from the shared group database.
    Use when the user says 'remove X', 'delete X', or 'I am done with X'.

    Args:
        topic: The research topic to remove.
    """
    try:
        r = httpx.delete(f"{API_BASE}/interests/{topic}", headers=HEADERS, timeout=5.0)
        if r.status_code == 200:
            return f"Removed '{topic}'."
        elif r.status_code == 404:
            return f"'{topic}' not found. Use list_interests to see what's saved."
        return f"Unexpected response: {r.status_code}"
    except httpx.HTTPError as e:
        return f"Could not reach the shared server: {str(e)}"


if __name__ == "__main__":
    mcp.run(transport="stdio")
