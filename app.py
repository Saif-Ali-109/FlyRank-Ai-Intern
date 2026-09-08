"""Task API — a tiny CRUD service built with FastAPI.

Routes are thin: every database operation goes through TaskRepository.
Swap the storage backend by changing repository.py only — the routes
and API contract stay identical.
"""

import os

from fastapi import FastAPI, Query
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from repository import TaskRepository

# ---------------------------------------------------------------------------
# Repository — the ONLY thing that touches the database
# ---------------------------------------------------------------------------

repo = TaskRepository(os.environ.get("DB_PATH", "tasks.db"))


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
    version="3.0",
    description="A small to-do list API — routes are storage-agnostic, backed by SQLite via TaskRepository.",
)


@app.get("/", summary="Describe this API")
def root():
    """Front door: returns the API's name, version and main resource."""
    return {"name": "Task API", "version": "3.0", "endpoints": ["/tasks"]}


@app.get("/health", summary="Liveness check")
def health():
    """Return {'status': 'ok'} so machines can confirm the server is alive."""
    return {"status": "ok"}


@app.get("/stats", summary="Summary counts")
def stats():
    """Return total / done / open counts via SQL COUNT()."""
    return repo.stats()


@app.get("/tasks", summary="List tasks (optional filter, search & sort)")
def list_tasks(
    done: bool | None = None,
    search: str | None = None,
    sort: str | None = Query(None, description="Sort order: 'asc' or 'desc' (by title)"),
):
    """Return all tasks. Optional query params:
    ?done=true/false  — filter by completion state
    ?search=word      — keep tasks whose title contains that word
    ?sort=asc/desc    — sort alphabetically by title
    """
    return repo.get_all(done=done, search=search, sort=sort)


@app.get("/tasks/{task_id}", summary="Get one task")
def get_task(task_id: int):
    """Return the task with this id, or 404 if it doesn't exist."""
    task = repo.get_by_id(task_id)
    if task is None:
        return JSONResponse(status_code=404, content={"error": f"Task {task_id} not found"})
    return task


@app.post("/tasks", status_code=201, summary="Create a task")
def create_task(payload: TaskCreate):
    """Create a task with done=False. Empty title → 400."""
    title = (payload.title or "").strip()
    if not title:
        return JSONResponse(
            status_code=400,
            content={"error": "title is required and cannot be empty"},
        )
    return repo.create(title)


@app.put("/tasks/{task_id}", summary="Update a task")
def update_task(task_id: int, payload: TaskUpdate):
    """Update title and/or done. Unknown id → 404, empty/invalid body → 400."""
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

    task = repo.update(
        task_id,
        title=payload.title.strip() if payload.title is not None else None,
        done=payload.done,
    )
    if task is None:
        return JSONResponse(status_code=404, content={"error": f"Task {task_id} not found"})
    return task


@app.delete("/tasks/{task_id}", status_code=204, summary="Delete a task")
def delete_task(task_id: int):
    """Remove the task. Unknown id → 404, success → 204 with an empty body."""
    if not repo.delete(task_id):
        return JSONResponse(status_code=404, content={"error": f"Task {task_id} not found"})
    return JSONResponse(status_code=204, content=None)


@app.post("/reset", summary="Reset to the 3 seed tasks")
def reset():
    """Delete all tasks and re-seed the original 3. Handy for demos."""
    tasks = repo.reset()
    return {"message": "reset to 3 tasks", "tasks": tasks}
