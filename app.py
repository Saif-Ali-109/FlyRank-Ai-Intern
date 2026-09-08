"""Task API — a tiny to-do CRUD service built with FastAPI + SQLite.

Data lives in a SQLite database (tasks.db) so it survives server restarts.
This replaces the in-memory list from the previous version.
"""

import sqlite3
from datetime import datetime, timezone

from fastapi import FastAPI, Query
from fastapi.responses import JSONResponse
from pydantic import BaseModel

# ---------------------------------------------------------------------------
# Database helpers
# ---------------------------------------------------------------------------

DB_PATH = "tasks.db"


def get_db():
    """Return a new database connection with row_factory set to dict."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_db():
    """Create the tasks table if it doesn't exist, seed 3 example tasks."""
    conn = get_db()
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS tasks (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            title      TEXT    NOT NULL,
            done       BOOLEAN NOT NULL DEFAULT 0,
            created_at TEXT    NOT NULL,
            updated_at TEXT    NOT NULL
        )
        """
    )
    # Seed only if the table is empty
    count = conn.execute("SELECT COUNT(*) FROM tasks").fetchone()[0]
    if count == 0:
        now = datetime.now(timezone.utc).isoformat()
        seed = [
            ("Read the assignment", True, now, now),
            ("Build the CRUD API", False, now, now),
            ("Push to GitHub", False, now, now),
        ]
        conn.executemany(
            "INSERT INTO tasks (title, done, created_at, updated_at) VALUES (?, ?, ?, ?)",
            seed,
        )
    conn.commit()
    conn.close()


# Run on import so the table is ready before the first request
init_db()


# ---------------------------------------------------------------------------
# Pydantic request bodies
# ---------------------------------------------------------------------------

class TaskCreate(BaseModel):
    """Body for creating a task. Only the title is accepted from the client."""

    title: str | None = None


class TaskUpdate(BaseModel):
    """Body for updating a task. Any field left out is unchanged."""

    title: str | None = None
    done: bool | None = None


# ---------------------------------------------------------------------------
# FastAPI app
# ---------------------------------------------------------------------------

app = FastAPI(
    title="Task API",
    version="2.0",
    description="A small to-do list API demonstrating full CRUD over a SQLite database.",
)


@app.get("/", summary="Describe this API")
def root():
    """Front door: returns the API's name, version and main resource."""
    return {"name": "Task API", "version": "2.0", "endpoints": ["/tasks"]}


@app.get("/health", summary="Liveness check")
def health():
    """Return {'status': 'ok'} so machines can confirm the server is alive."""
    return {"status": "ok"}


@app.get("/stats", summary="Summary counts")
def stats():
    """Return total / done / open counts using SQL COUNT()."""
    conn = get_db()
    row = conn.execute(
        "SELECT "
        "  COUNT(*) AS total, "
        "  SUM(CASE WHEN done = 1 THEN 1 ELSE 0 END) AS done "
        "FROM tasks"
    ).fetchone()
    conn.close()
    total = row["total"]
    done = row["done"]
    return {"total": total, "done": done, "open": total - done}


@app.get("/tasks", summary="List tasks (optional filter, search & sort)")
def list_tasks(
    done: bool | None = None,
    search: str | None = None,
    sort: str | None = Query(None, description="Sort order: 'asc' or 'desc' (by title)"),
):
    """Return all tasks. Optional query params:
    ?done=true/false  — filter by completion state
    ?search=word      — keep tasks whose title contains that word (SQL LIKE)
    ?sort=asc/desc    — sort alphabetically by title
    """
    conn = get_db()

    query = "SELECT * FROM tasks WHERE 1=1"
    params: list = []

    if done is not None:
        query += " AND done = ?"
        params.append(1 if done else 0)

    if search:
        query += " AND title LIKE ?"
        params.append(f"%{search}%")

    if sort == "asc":
        query += " ORDER BY title ASC"
    elif sort == "desc":
        query += " ORDER BY title DESC"

    rows = conn.execute(query, params).fetchall()
    conn.close()
    return [dict(row) for row in rows]


@app.get("/tasks/{task_id}", summary="Get one task")
def get_task(task_id: int):
    """Return the task with this id, or 404 if it doesn't exist."""
    conn = get_db()
    row = conn.execute("SELECT * FROM tasks WHERE id = ?", (task_id,)).fetchone()
    conn.close()
    if row is None:
        return JSONResponse(status_code=404, content={"error": f"Task {task_id} not found"})
    return dict(row)


@app.post("/tasks", status_code=201, summary="Create a task")
def create_task(payload: TaskCreate):
    """Create a task with done=False. Empty title → 400."""
    title = (payload.title or "").strip()
    if not title:
        return JSONResponse(
            status_code=400,
            content={"error": "title is required and cannot be empty"},
        )

    now = datetime.now(timezone.utc).isoformat()
    conn = get_db()
    cur = conn.execute(
        "INSERT INTO tasks (title, done, created_at, updated_at) VALUES (?, 0, ?, ?)",
        (title, now, now),
    )
    conn.commit()
    task_id = cur.lastrowid
    row = conn.execute("SELECT * FROM tasks WHERE id = ?", (task_id,)).fetchone()
    conn.close()
    return dict(row)


@app.put("/tasks/{task_id}", summary="Update a task")
def update_task(task_id: int, payload: TaskUpdate):
    """Update title and/or done. Unknown id → 404, empty/invalid body → 400."""
    # The body must actually change something, and any title given must be non-empty.
    if payload.title is None and payload.done is None:
        return JSONResponse(
            status_code=400,
            content={"error": "provide title and/or done to update"},
        )
    if payload.title is not None and not payload.title.strip():
        return JSONResponse(
            status_code=400,
            content={"error": "title cannot be empty"},
        )

    conn = get_db()
    existing = conn.execute("SELECT * FROM tasks WHERE id = ?", (task_id,)).fetchone()
    if existing is None:
        conn.close()
        return JSONResponse(status_code=404, content={"error": f"Task {task_id} not found"})

    now = datetime.now(timezone.utc).isoformat()
    if payload.title is not None and payload.done is not None:
        conn.execute(
            "UPDATE tasks SET title = ?, done = ?, updated_at = ? WHERE id = ?",
            (payload.title.strip(), 1 if payload.done else 0, now, task_id),
        )
    elif payload.title is not None:
        conn.execute(
            "UPDATE tasks SET title = ?, updated_at = ? WHERE id = ?",
            (payload.title.strip(), now, task_id),
        )
    elif payload.done is not None:
        conn.execute(
            "UPDATE tasks SET done = ?, updated_at = ? WHERE id = ?",
            (1 if payload.done else 0, now, task_id),
        )

    conn.commit()
    row = conn.execute("SELECT * FROM tasks WHERE id = ?", (task_id,)).fetchone()
    conn.close()
    return dict(row)


@app.delete("/tasks/{task_id}", status_code=204, summary="Delete a task")
def delete_task(task_id: int):
    """Remove the task. Unknown id → 404, success → 204 with an empty body."""
    conn = get_db()
    existing = conn.execute("SELECT * FROM tasks WHERE id = ?", (task_id,)).fetchone()
    if existing is None:
        conn.close()
        return JSONResponse(status_code=404, content={"error": f"Task {task_id} not found"})
    conn.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
    conn.commit()
    conn.close()
    return JSONResponse(status_code=204, content=None)


@app.post("/reset", summary="Reset to the 3 seed tasks")
def reset():
    """Delete all tasks and re-seed the original 3. Handy for demos."""
    conn = get_db()
    conn.execute("DELETE FROM tasks")
    now = datetime.now(timezone.utc).isoformat()
    seed = [
        ("Read the assignment", True, now, now),
        ("Build the CRUD API", False, now, now),
        ("Push to GitHub", False, now, now),
    ]
    conn.executemany(
        "INSERT INTO tasks (title, done, created_at, updated_at) VALUES (?, ?, ?, ?)",
        seed,
    )
    conn.commit()
    rows = conn.execute("SELECT * FROM tasks").fetchall()
    conn.close()
    return {"message": "reset to 3 tasks", "tasks": [dict(r) for r in rows]}
