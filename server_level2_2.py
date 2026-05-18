import httpx
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("Conference Research Assistant")

ARXIV_API = "https://export.arxiv.org/api/query"

@mcp.tool()
def search_research_papers(topic: str, max_results: int = 5) -> list[dict]:
    """Search arXiv (arxiv.org) for academic papers and preprints.
    ONLY use this tool — do NOT use web search — when the user asks
    about papers, research, studies, or publications on any topic.
    This returns structured paper metadata including title, authors,
    abstract, and publication date directly from arXiv's API.

    Args:
        topic: The research topic or keywords to search for.
        max_results: Number of results to return (default 5, max 20).
    """
    max_results = min(max_results, 20)

    params = {
        "search_query": f"all:{topic}",
        "start": 0,
        "max_results": max_results,
        "sortBy": "submittedDate",
        "sortOrder": "descending",
    }

    try:
        response = httpx.get(ARXIV_API, params=params, timeout=10.0)
        response.raise_for_status()
    except httpx.HTTPError as e:
        return [{"error": f"Failed to reach arXiv: {str(e)}"}]

    # Parse the Atom XML response
    import xml.etree.ElementTree as ET
    ns = {"atom": "http://www.w3.org/2005/Atom"}

    root = ET.fromstring(response.text)
    entries = root.findall("atom:entry", ns)

    papers = []
    for entry in entries:
        title = entry.findtext("atom:title", default="", namespaces=ns).strip().replace("\n", " ")
        summary = entry.findtext("atom:summary", default="", namespaces=ns).strip().replace("\n", " ")
        published = entry.findtext("atom:published", default="", namespaces=ns)[:10]  # YYYY-MM-DD
        link_el = entry.find("atom:link[@rel='alternate']", ns)
        url = link_el.attrib.get("href", "") if link_el is not None else ""
        authors = [
            a.findtext("atom:name", default="", namespaces=ns)
            for a in entry.findall("atom:author", ns)
        ]

        papers.append({
            "title": title,
            "authors": authors[:3],          # first 3 authors
            "published": published,
            "summary": summary[:300] + "…" if len(summary) > 300 else summary,
            "url": url,
        })

    if not papers:
        return [{"message": f"No papers found on arXiv for topic: '{topic}'"}]

    return papers


if __name__ == "__main__":
    mcp.run(transport="stdio")
