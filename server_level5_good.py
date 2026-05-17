"""
Level 5 GOOD — conference_assistant_good_server.py
One well-designed find_conferences tool replaces all the narrow ones.
"""
import httpx
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("Conference Assistant — Good Design")

OPENALEX_URL = "https://api.openalex.org/works"
ARXIV_API    = "https://export.arxiv.org/api/query"
API_BASE     = "http://34.65.167.161:5556"
API_TOKEN    = "workshop-ch-open-2026"
YOUR_NAME    = "participant"   # ← change to your name
HEADERS      = {"Authorization": f"Bearer {API_TOKEN}"}
MAILTO       = "your@email.com"  # ← optional but gives higher rate limits


# ── Level 5 tool — ONE tool replaces FIVE ─────────────────────────────────────

@mcp.tool()
def find_conferences(
    topic: str = "",
    year: int = 0,
    open_access_only: bool = False,
    min_citations: int = 0,
    max_results: int = 10,
) -> list[dict]:
    """Search for conference papers using OpenAlex (no API key needed).
    Use this tool whenever the user asks about conferences, conference papers,
    talks, or published proceedings — whether they mention a topic, year,
    open access, citation count, or any combination. Apply all filters in
    a single call — never call this tool multiple times for one question.

    Args:
        topic: Topic or keyword to search for (leave empty for no keyword filter).
        year: Filter by publication year (0 = no year filter).
        open_access_only: If True, return only open access papers.
        min_citations: Minimum citation count (0 = no filter).
        max_results: Number of results to return (default 10, max 25).
    """
    max_results = min(max_results, 25)

    filters = ["type:article", "primary_location.source.type:conference"]
    if year:
        filters.append(f"publication_year:{year}")
    if open_access_only:
        filters.append("open_access.is_oa:true")
    if min_citations:
        filters.append(f"cited_by_count:>{min_citations}")

    params = {
        "filter":   ",".join(filters),
        "sort":     "publication_date:desc",
        "per_page": max_results,
        "mailto":   MAILTO,
    }
    if topic:
        params["search"] = topic

    try:
        r = httpx.get(OPENALEX_URL, params=params, timeout=10.0)
        r.raise_for_status()
        results = r.json().get("results", [])
    except httpx.HTTPError as e:
        return [{"error": f"Failed to reach OpenAlex: {str(e)}"}]

    if not results:
        return [{"message": "No conference papers found for the given filters."}]

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
