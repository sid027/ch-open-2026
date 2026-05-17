import sqlite3
from pathlib import Path
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("Conference Research Assistant")

# ── SQLite setup ───────────────────────────────────────────────────────────────

DB_PATH = Path(__file__).parent / "database" / "interests.db"

def get_db():
    """Return a database connection, creating the schema if needed."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("""
        CREATE TABLE IF NOT EXISTS interests (
            id        INTEGER PRIMARY KEY AUTOINCREMENT,
            topic     TEXT NOT NULL UNIQUE,
            added_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    return conn

# ── Level 3 tools (new) ────────────────────────────────────────────────────────

@mcp.tool()
def add_interest(topic: str) -> str:
    """Save a new research interest or topic so it is remembered across conversations.
    Use this when the user says things like 'remember that I am researching X',
    'add X to my interests', or 'I am interested in X'.

    Args:
        topic: The research topic or interest to remember.
    """
    try:
        with get_db() as conn:
            conn.execute("INSERT INTO interests (topic) VALUES (?)", (topic,))
            conn.commit()
        return f"✅ Added '{topic}' to your research interests."
    except sqlite3.IntegrityError:
        return f"ℹ️ '{topic}' is already in your research interests."


@mcp.tool()
def list_interests() -> list[dict]:
    """Return all saved research interests with the date they were added.
    Use this when the user asks what they are researching, what topics they 
    have saved, or what they are interested in.
    """
    with get_db() as conn:
        rows = conn.execute(
            "SELECT topic, added_at FROM interests ORDER BY added_at DESC"
        ).fetchall()
    if not rows:
        return [{"message": "No interests saved yet. Try asking me to remember a topic!"}]
    return [{"topic": r["topic"], "added_at": r["added_at"]} for r in rows]


@mcp.tool()
def remove_interest(topic: str) -> str:
    """Remove a research interest that is no longer relevant.
    Use this when the user says 'remove X', 'I am no longer interested in X',
    or 'delete X from my interests'.

    Args:
        topic: The research topic to remove.
    """
    with get_db() as conn:
        cursor = conn.execute("DELETE FROM interests WHERE topic = ?", (topic,))
        conn.commit()
    if cursor.rowcount > 0:
        return f"🗑️ Removed '{topic}' from your research interests."
    return f"⚠️ '{topic}' was not found in your interests. Use list_interests to see what's saved."


if __name__ == "__main__":
    mcp.run(transport="stdio")
