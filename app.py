"""Task API — a tiny in-memory to-do CRUD service built with FastAPI.

Data lives in a plain Python list, so it resets every time the server
restarts. That is intentional (see the "mortality experiment" in the README):
databases exist precisely to fix this, and that is next week's lesson.
"""

from fastapi import FastAPI
from fastapi.responses import JSONResponse
from pydantic import BaseModel

app = FastAPI(
    title="Task API",
    version="1.0",
    description="A small to-do list API demonstrating full CRUD over an in-memory list.",
)

# In-memory "database": a plain list of task dicts, pre-filled with 3 tasks.
# Gone the moment the process stops — that's the point (see Week 3).
tasks = [
    {"id": 1, "title": "Read the assignment", "done": True},
    {"id": 2, "title": "Build the CRUD API", "done": False},
    {"id": 3, "title": "Push to GitHub", "done": False},
]


class TaskCreate(BaseModel):
    """Body for creating a task. Only the title is accepted from the client."""

    title: str | None = None


class TaskUpdate(BaseModel):
    """Body for updating a task. Any field left out is unchanged."""

    title: str | None = None
    done: bool | None = None


def find_task(task_id: int):
    """Return the task dict with this id, or None if there isn't one."""
    for task in tasks:
        if task["id"] == task_id:
            return task
    return None


def next_id():
    """Next free id = one past the current highest id (1 if the list is empty)."""
    return max((t["id"] for t in tasks), default=0) + 1


@app.get("/", summary="Describe this API")
def root():
    """Front door: returns the API's name, version and main resource."""
    return {"name": "Task API", "version": "1.0", "endpoints": ["/tasks"]}


@app.get("/health", summary="Liveness check")
def health():
    """Return {'status': 'ok'} so machines can confirm the server is alive."""
    return {"status": "ok"}


@app.get("/stats", summary="Summary counts")
def stats():
    """Compute totals instead of just storing — total / done / open tasks."""
    done = sum(1 for t in tasks if t["done"])
    return {"total": len(tasks), "done": done, "open": len(tasks) - done}


@app.get("/tasks", summary="List tasks (optional filter & search)")
def list_tasks(done: bool | None = None, search: str | None = None):
    """Return all tasks. Optional ?done=true/false filters by state;
    optional ?search=word keeps tasks whose title contains that word."""
    result = tasks
    if done is not None:
        result = [t for t in result if t["done"] == done]
    if search:
        needle = search.lower()
        result = [t for t in result if needle in t["title"].lower()]
    return result


@app.get("/tasks/{task_id}", summary="Get one task")
def get_task(task_id: int):
    """Return the task with this id, or 404 if it doesn't exist."""
    task = find_task(task_id)
    if task is None:
        return JSONResponse(status_code=404, content={"error": f"Task {task_id} not found"})
    return task


@app.post("/tasks", status_code=201, summary="Create a task")
def create_task(payload: TaskCreate):
    """Create a task with a fresh id and done=False. Empty title → 400."""
    title = (payload.title or "").strip()
    if not title:
        return JSONResponse(status_code=400, content={"error": "title is required and cannot be empty"})
    task = {"id": next_id(), "title": title, "done": False}
    tasks.append(task)
    return task


@app.put("/tasks/{task_id}", summary="Update a task")
def update_task(task_id: int, payload: TaskUpdate):
    """Update title and/or done. Unknown id → 404, empty/invalid body → 400."""
    task = find_task(task_id)
    if task is None:
        return JSONResponse(status_code=404, content={"error": f"Task {task_id} not found"})

    # The body must actually change something, and any title given must be non-empty.
    if payload.title is None and payload.done is None:
        return JSONResponse(status_code=400, content={"error": "provide title and/or done to update"})
    if payload.title is not None and not payload.title.strip():
        return JSONResponse(status_code=400, content={"error": "title cannot be empty"})

    if payload.title is not None:
        task["title"] = payload.title.strip()
    if payload.done is not None:
        task["done"] = payload.done
    return task


@app.delete("/tasks/{task_id}", status_code=204, summary="Delete a task")
def delete_task(task_id: int):
    """Remove the task. Unknown id → 404, success → 204 with an empty body."""
    task = find_task(task_id)
    if task is None:
        return JSONResponse(status_code=404, content={"error": f"Task {task_id} not found"})
    tasks.remove(task)
    return JSONResponse(status_code=204, content=None)


@app.post("/reset", summary="Reset to the 3 seed tasks")
def reset():
    """Restore the original 3 example tasks. Handy for demos."""
    global tasks
    tasks = [
        {"id": 1, "title": "Read the assignment", "done": True},
        {"id": 2, "title": "Build the CRUD API", "done": False},
        {"id": 3, "title": "Push to GitHub", "done": False},
    ]
    return {"message": "reset to 3 tasks", "tasks": tasks}
