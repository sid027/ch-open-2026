from mcp.server.fastmcp import FastMCP

# Initialize the MCP server
mcp = FastMCP("Conference Research Assistant")

# Hardcoded list of research interests
TOPICS = [
    "LLM agent orchestration",
    "Model Context Protocol (MCP)",
    "Retrieval-Augmented Generation (RAG)",
    "Transformer architectures",
    "Distributed systems",
]

@mcp.tool()
def get_topics() -> list[str]:
    """Returns the list of research topics I am currently interested in."""
    return TOPICS

@mcp.tool()
def greet_participants(event_name: str) -> str:
    """Greet the workshop participants with a welcome message.
    
    Args:
        event_name: The name of the workshop or event.
    """
    topics_str = ", ".join(TOPICS)
    return (
        f"Welcome to {event_name}! 👋\n\n"
        f"Today we are building an MCP server step by step.\n"
        f"By the end, you will be able to answer:\n"
        f"'I'm going to a tech conference — which talks match my research?'\n\n"
        f"Current research topics loaded: {topics_str}"
    )

if __name__ == "__main__":
    mcp.run(transport="stdio")
