"""
Instructor-deployed REST API — runs on 34.65.167.161:5556
Exposes the shared interests database over HTTP.
"""
import sqlite3
from pathlib import Path
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Header
from pydantic import BaseModel

DB_PATH = Path(__file__).parent / "interests.db"
API_TOKEN = "workshop-ch-open-2026"  # share this token with participants

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("""
        CREATE TABLE IF NOT EXISTS interests (
            id        INTEGER PRIMARY KEY AUTOINCREMENT,
            topic     TEXT NOT NULL UNIQUE,
            added_by  TEXT NOT NULL DEFAULT 'participant',
            added_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    return conn

def require_auth(authorization: str = Header(None)):
    if authorization != f"Bearer {API_TOKEN}":
        raise HTTPException(status_code=401, detail="Invalid or missing token")

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Seed with a few starter interests so the DB is not empty on first connect
    with get_db() as conn:
        for topic in ["Model Context Protocol (MCP)", "LLM agent orchestration"]:
            try:
                conn.execute(
                    "INSERT INTO interests (topic, added_by) VALUES (?, ?)",
                    (topic, "instructor")
                )
            except sqlite3.IntegrityError:
                pass
        conn.commit()
    yield

app = FastAPI(title="Conference Research API", lifespan=lifespan)

class InterestIn(BaseModel):
    topic: str
    added_by: str = "participant"

@app.get("/interests")
def list_interests(authorization: str = Header(None)):
    require_auth(authorization)
    with get_db() as conn:
        rows = conn.execute(
            "SELECT topic, added_by, added_at FROM interests ORDER BY added_at DESC"
        ).fetchall()
    return [dict(r) for r in rows]

@app.post("/interests")
def add_interest(body: InterestIn, authorization: str = Header(None)):
    require_auth(authorization)
    try:
        with get_db() as conn:
            conn.execute(
                "INSERT INTO interests (topic, added_by) VALUES (?, ?)",
                (body.topic, body.added_by)
            )
            conn.commit()
        return {"status": "added", "topic": body.topic}
    except sqlite3.IntegrityError:
        return {"status": "exists", "topic": body.topic}

@app.delete("/interests/{topic}")
def remove_interest(topic: str, authorization: str = Header(None)):
    require_auth(authorization)
    with get_db() as conn:
        cursor = conn.execute("DELETE FROM interests WHERE topic = ?", (topic,))
        conn.commit()
    if cursor.rowcount == 0:
        raise HTTPException(status_code=404, detail=f"Topic '{topic}' not found")
    return {"status": "removed", "topic": topic}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=5556)
