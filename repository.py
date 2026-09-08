"""TaskRepository — all SQLite storage logic lives here.

This is the ONLY file that touches the database.  When we later swap
SQLite for PostgreSQL (or anything else), we change this file and
nothing else.  The routes in app.py call these methods and stay
completely storage-agnostic.
"""

import sqlite3
from datetime import datetime, timezone
from pathlib import Path


class TaskRepository:
    """CRUD operations over a SQLite tasks table."""

    def __init__(self, db_path: str = "tasks.db"):
        self.db_path = db_path
        # Ensure the parent directory exists (important for Docker /data/)
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _connect(self) -> sqlite3.Connection:
        """Return a new connection with row_factory set."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA foreign_keys=ON")
        return conn

    def _init_db(self):
        """Create the tasks table if missing; seed 3 examples if empty."""
        conn = self._connect()
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
        count = conn.execute("SELECT COUNT(*) FROM tasks").fetchone()[0]
        if count == 0:
            now = datetime.now(timezone.utc).isoformat()
            conn.executemany(
                "INSERT INTO tasks (title, done, created_at, updated_at) VALUES (?, ?, ?, ?)",
                [
                    ("Read the assignment", True, now, now),
                    ("Build the CRUD API", False, now, now),
                    ("Push to GitHub", False, now, now),
                ],
            )
        conn.commit()
        conn.close()

    # ------------------------------------------------------------------
    # Public CRUD methods
    # ------------------------------------------------------------------

    def get_all(self, done: bool | None = None, search: str | None = None,
                sort: str | None = None) -> list[dict]:
        """Return all tasks, optionally filtered and sorted."""
        conn = self._connect()
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
        return [dict(r) for r in rows]

    def get_by_id(self, task_id: int) -> dict | None:
        """Return one task or None."""
        conn = self._connect()
        row = conn.execute("SELECT * FROM tasks WHERE id = ?", (task_id,)).fetchone()
        conn.close()
        return dict(row) if row else None

    def create(self, title: str) -> dict:
        """Insert a new task and return it."""
        now = datetime.now(timezone.utc).isoformat()
        conn = self._connect()
        cur = conn.execute(
            "INSERT INTO tasks (title, done, created_at, updated_at) VALUES (?, 0, ?, ?)",
            (title, now, now),
        )
        conn.commit()
        task_id = cur.lastrowid
        row = conn.execute("SELECT * FROM tasks WHERE id = ?", (task_id,)).fetchone()
        conn.close()
        return dict(row)

    def update(self, task_id: int, title: str | None = None,
               done: bool | None = None) -> dict | None:
        """Update fields and return the task, or None if not found."""
        conn = self._connect()
        existing = conn.execute("SELECT * FROM tasks WHERE id = ?", (task_id,)).fetchone()
        if not existing:
            conn.close()
            return None

        now = datetime.now(timezone.utc).isoformat()
        if title is not None and done is not None:
            conn.execute(
                "UPDATE tasks SET title = ?, done = ?, updated_at = ? WHERE id = ?",
                (title, 1 if done else 0, now, task_id),
            )
        elif title is not None:
            conn.execute(
                "UPDATE tasks SET title = ?, updated_at = ? WHERE id = ?",
                (title, now, task_id),
            )
        elif done is not None:
            conn.execute(
                "UPDATE tasks SET done = ?, updated_at = ? WHERE id = ?",
                (1 if done else 0, now, task_id),
            )

        conn.commit()
        row = conn.execute("SELECT * FROM tasks WHERE id = ?", (task_id,)).fetchone()
        conn.close()
        return dict(row)

    def delete(self, task_id: int) -> bool:
        """Delete a task. Returns True if it existed."""
        conn = self._connect()
        existing = conn.execute("SELECT * FROM tasks WHERE id = ?", (task_id,)).fetchone()
        if not existing:
            conn.close()
            return False
        conn.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
        conn.commit()
        conn.close()
        return True

    def stats(self) -> dict:
        """Return total / done / open counts via SQL."""
        conn = self._connect()
        row = conn.execute(
            "SELECT COUNT(*) AS total, "
            "SUM(CASE WHEN done = 1 THEN 1 ELSE 0 END) AS done "
            "FROM tasks"
        ).fetchone()
        conn.close()
        total = row["total"]
        done = row["done"]
        return {"total": total, "done": done, "open": total - done}

    def reset(self) -> list[dict]:
        """Delete all tasks and re-seed the 3 originals."""
        conn = self._connect()
        conn.execute("DELETE FROM tasks")
        now = datetime.now(timezone.utc).isoformat()
        conn.executemany(
            "INSERT INTO tasks (title, done, created_at, updated_at) VALUES (?, ?, ?, ?)",
            [
                ("Read the assignment", True, now, now),
                ("Build the CRUD API", False, now, now),
                ("Push to GitHub", False, now, now),
            ],
        )
        conn.commit()
        rows = conn.execute("SELECT * FROM tasks").fetchall()
        conn.close()
        return [dict(r) for r in rows]
