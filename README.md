# Task API — W2 · A1

A tiny **to-do list API** demonstrating full **CRUD** (Create, Read, Update, Delete)
over an **in-memory** list, built with **FastAPI**. Swagger UI is included for free
at `/docs`.

There is no database on purpose: the data lives in a plain Python list, so it resets
every time the server restarts. That is next week's lesson — see the
[Mortality experiment](#the-mortality-experiment) below.

## Install & run

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
uvicorn app:app --reload
```

The server starts on **http://localhost:8000**.
Open **http://localhost:8000/docs** for interactive Swagger UI.

## Endpoints

| Method | Path            | CRUD   | Success | Errors                          | Meaning                          |
|--------|-----------------|--------|---------|---------------------------------|----------------------------------|
| GET    | `/`             | —      | 200     | —                               | Describe the API                 |
| GET    | `/health`       | —      | 200     | —                               | Liveness check                   |
| GET    | `/tasks`        | Read   | 200     | —                               | List all tasks                   |
| GET    | `/tasks/{id}`   | Read   | 200     | 404 unknown id                  | Get one task                     |
| POST   | `/tasks`        | Create | 201     | 400 empty/missing title         | Create a task                    |
| PUT    | `/tasks/{id}`   | Update | 200     | 400 empty/invalid body, 404 id  | Update title and/or done         |
| DELETE | `/tasks/{id}`   | Delete | 204     | 404 unknown id                  | Remove a task                    |

Every error returns a JSON body of the shape `{ "error": "..." }`.

### Extras (optional, built for fun)

| Method | Path                    | Meaning                                        |
|--------|-------------------------|------------------------------------------------|
| GET    | `/tasks?done=true`      | Filter by completion state                     |
| GET    | `/tasks?search=milk`    | Keep tasks whose title contains the word       |
| GET    | `/stats`                | `{ "total": 3, "done": 1, "open": 2 }`         |
| POST   | `/reset`                | Restore the 3 original seed tasks              |

## Example: `curl -i`

```
$ curl -i -X POST http://localhost:8000/tasks \
       -H "Content-Type: application/json" \
       -d '{"title":"Buy milk"}'

HTTP/1.1 201 Created
date: Mon, 20 Jul 2026 17:44:49 GMT
server: uvicorn
content-length: 40
content-type: application/json

{"id":4,"title":"Buy milk","done":false}
```

## Swagger UI

![Swagger UI showing all endpoints](swagger-ui.png)

Use **Try it out** on any endpoint to run the full CRUD cycle without curl.

## The mortality experiment

Create a few tasks, restart the server, then `GET /tasks`. **Your new tasks are gone**
and only the 3 seed tasks remain. That happens because the task list lives only in the
process's memory (a Python variable) — when the process stops, the memory is freed and
the list is rebuilt from scratch on the next start. A database (next week) persists data
to disk precisely so it survives restarts.

## AI vs me

**My prompt** (written from memory, not copied from the assignment):

> Build a to-do list REST API in Python with FastAPI, storing tasks in an in-memory
> list (no database). Each task has an integer `id`, a string `title`, and a boolean
> `done`. Seed it with 3 example tasks. Implement five endpoints: `GET /tasks` (list
> all), `GET /tasks/{id}` (one task, 404 if missing), `POST /tasks` (create from a JSON
> body with just a title, assign the next id, done=false, return 201), `PUT /tasks/{id}`
> (update title and/or done, 404 if missing), and `DELETE /tasks/{id}` (remove, return
> 204). Validate input: a missing or empty title must return 400. Use the built-in
> Swagger UI at `/docs`.

The AI's code lives in [`ai-version/main.py`](ai-version/main.py), untouched, so my
hand-built `app.py` stays hand-built. I ran it on port 8001 and fired my Stage 4
checkpoint curls at it. Three concrete differences:

1. **Wrong status code for a missing body.** `POST /tasks` with `{}` returned **422**,
   not the **400** my prompt asked for. The AI leaned on FastAPI's automatic Pydantic
   validation (a required `title` field), which raises 422 for a malformed body. I
   understand it: 422 *is* the technically-correct FastAPI default, but it silently
   ignored my explicit "400" rule.

2. **A validation rule it quietly dropped.** `POST /tasks` with `{"title":"   "}`
   (whitespace only) returned **201** and happily created a blank task. My version
   `.strip()`s the title and rejects it with 400. The AI treated "empty" as "empty
   string" only, not "empty after trimming".

3. **Different error shape + a silent decision on PUT.** The AI returns
   `{"detail": "..."}` (FastAPI's `HTTPException` default), while mine returns
   `{"error": "..."}`. And `PUT /tasks/{id}` with an empty body `{}` returned **200**
   (a no-op update) rather than the **400** I chose — my prompt never said what an empty
   update body should do, so the AI decided for me.

**What my prompt forgot to specify:** the exact JSON error shape, whether whitespace-only
titles count as empty, and what an empty PUT body should do. The AI filled all three gaps
with reasonable-but-different defaults.

**One rematch:** I would add one sentence — *"All errors must return `{"error": "..."}`
with status 400 for any invalid or empty body (including whitespace-only titles) and 404
for unknown ids; do not rely on FastAPI's default 422."* That single clause closes all
three gaps at once.

> The lesson: the AI's output was exactly as good as my specification. I could only spot
> the gaps because I had already built the thing by hand and knew what "correct" looked
> like.
