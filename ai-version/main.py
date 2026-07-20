"""
Task API (AI-generated version) — Stage 7 "AI rematch".

This file was produced from the prompt in the README's "AI vs me" section,
then committed UNCHANGED so it can be diffed honestly against the hand-built
../app.py. It intentionally reflects idiomatic FastAPI choices an assistant
tends to reach for: Pydantic field validation and HTTPException rather than
hand-rolled JSONResponse error bodies.
"""

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

app = FastAPI(title="Task API (AI version)", version="1.0")

# In-memory store.
tasks = [
    {"id": 1, "title": "Read the assignment", "done": True},
    {"id": 2, "title": "Build the CRUD API", "done": False},
    {"id": 3, "title": "Push to GitHub", "done": False},
]


class TaskIn(BaseModel):
    # min_length=1 makes an empty title a 422 automatically.
    title: str = Field(..., min_length=1)


class TaskPatch(BaseModel):
    title: str | None = Field(None, min_length=1)
    done: bool | None = None


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
    for task in tasks:
        if task["id"] == task_id:
            return task
    raise HTTPException(status_code=404, detail=f"Task {task_id} not found")


@app.post("/tasks", status_code=201)
def create_task(payload: TaskIn):
    new_id = max((t["id"] for t in tasks), default=0) + 1
    task = {"id": new_id, "title": payload.title, "done": False}
    tasks.append(task)
    return task


@app.put("/tasks/{task_id}")
def update_task(task_id: int, payload: TaskPatch):
    for task in tasks:
        if task["id"] == task_id:
            if payload.title is not None:
                task["title"] = payload.title
            if payload.done is not None:
                task["done"] = payload.done
            return task
    raise HTTPException(status_code=404, detail=f"Task {task_id} not found")


@app.delete("/tasks/{task_id}", status_code=204)
def delete_task(task_id: int):
    for i, task in enumerate(tasks):
        if task["id"] == task_id:
            tasks.pop(i)
            return
    raise HTTPException(status_code=404, detail=f"Task {task_id} not found")
