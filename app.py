from fastapi import FastAPI
from fastapi.responses import JSONResponse
from pydantic import BaseModel

app = FastAPI()

# In-memory "database": a plain list of task dicts.
# It resets every time the server restarts — that's the point (see Week 3).
tasks = [
    {"id": 1, "title": "Read the assignment", "done": True},
    {"id": 2, "title": "Build the CRUD API", "done": False},
    {"id": 3, "title": "Push to GitHub", "done": False},
]


class TaskCreate(BaseModel):
    title: str | None = None


class TaskUpdate(BaseModel):
    title: str | None = None
    done: bool | None = None


def find_task(task_id: int):
    for task in tasks:
        if task["id"] == task_id:
            return task
    return None


def next_id():
    return max((t["id"] for t in tasks), default=0) + 1


@app.get("/")
def root():
    return {"name": "Task API", "version": "1.0", "endpoints": ["/tasks"]}


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/tasks")
def list_tasks():
    return tasks


@app.get("/tasks/{task_id}")
def get_task(task_id: int):
    task = find_task(task_id)
    if task is None:
        return JSONResponse(status_code=404, content={"error": f"Task {task_id} not found"})
    return task


@app.post("/tasks", status_code=201)
def create_task(payload: TaskCreate):
    title = (payload.title or "").strip()
    if not title:
        return JSONResponse(status_code=400, content={"error": "title is required and cannot be empty"})
    task = {"id": next_id(), "title": title, "done": False}
    tasks.append(task)
    return task


@app.put("/tasks/{task_id}")
def update_task(task_id: int, payload: TaskUpdate):
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


@app.delete("/tasks/{task_id}", status_code=204)
def delete_task(task_id: int):
    task = find_task(task_id)
    if task is None:
        return JSONResponse(status_code=404, content={"error": f"Task {task_id} not found"})
    tasks.remove(task)
    return JSONResponse(status_code=204, content=None)
