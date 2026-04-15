# Choose Your Own Adventure API 

## Overview
This service is a FastAPI backend that generates branching "choose your own adventure" stories using an LLM (Groq API), stores stories and nodes in a SQL database via SQLAlchemy, and exposes API endpoints for asynchronous story generation and retrieval.

The project creates a background job when a story is requested. The client first receives a `job_id`, then polls a job-status endpoint until generation is complete, and finally fetches the full generated story tree.

## Tech Stack
- Python 3.14+
- FastAPI + Uvicorn
- SQLAlchemy ORM
- Pydantic / Pydantic Settings
- httpx (LLM HTTP calls)
- Groq Chat Completions API
- SQLite by default (configurable through `DATABASE_URL`)

## Production Environment Variables
Create a `.env` file in the project root.

Required and supported settings:

- `GROQ_API_KEY`:
  - Required.
  - Used by `core/story_generator.py` for authenticated LLM calls.
- `DATABASE_URL`:
  - Optional (default: `sqlite:///./database.db`).
  - Set this to a production-grade database URL in production.
- `API_PREFIX`:
  - Optional (default: `/api`).
- `ALLOWED_ORIGINS`:
  - Optional.
  - Comma-separated list of origins for CORS. Example: `https://app.example.com,https://admin.example.com`
- `DEBUG`:
  - Optional (default: `False`).

Example:

```env
GROQ_API_KEY=your_groq_api_key_here
DATABASE_URL=postgresql+psycopg2://user:password@host:5432/choose_adventure
API_PREFIX=/api
ALLOWED_ORIGINS=https://app.example.com,https://admin.example.com
DEBUG=False
```

## Install and Run
From the project root:

```bash
uv sync
uv run uvicorn main:app --host 0.0.0.0 --port 8000
```

or simply:
```bash
uv run main.py
```

Notes:
- `create_tables()` is executed on app startup in `main.py`, so tables are auto-created from SQLAlchemy models.
- For production, it is however recommended to run behind a reverse proxy and use process management 

## API Base URLs
- Local service base: `http://localhost:8000`
- API base (default prefix): `http://localhost:8000/api`
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

## Endpoints and Flow
Current routers are mounted under `API_PREFIX` and split by domain:

- Stories router (`/stories`): create story job + fetch full story
- Jobs router (`/jobs`): query job status

Typical client flow:

1. POST a story-generation request (`theme`) to create a job.
2. Receive `job_id` with initial status.
3. Poll job status until it becomes `completed` (or `failed`).
4. Use returned `story_id` to fetch full story tree.

## Step-by-Step: Test Swagger Docs (Required Flow)
Use these exact steps in Swagger so the async workflow is tested correctly.

### Step 1: Start the API
Run:

```bash
uv run uvicorn main:app --host 0.0.0.0 --port 8000
```

Confirm service is up by opening:
- `http://localhost:8000/docs`

### Step 2: Open Swagger UI
In browser, open:
- `http://localhost:8000/docs`

You should see two tags:
- `stories`
- `jobs`

### Step 3: Create a Story Job
In Swagger:

1. Expand `POST /api/stories/`.
2. Click **Try it out**.
3. Provide request body, for example:

```json
{
  "theme": "space pirates"
}
```

4. Click **Execute**.
5. Verify response includes:
   - `job_id`
   - `status` (typically `pending` first)

Important behavior:
- A `session_id` cookie is set by this endpoint.
- Story generation runs in a FastAPI background task after the response returns.

### Step 4: Poll Job Status Until Complete
In Swagger, use the jobs status endpoint repeatedly.

1. Expand `GET /api/jobs/{job.id}`.
2. Click **Try it out**.
3. Paste the `job_id` from Step 3 into the path parameter input.
4. Click **Execute**.
5. Observe `status` transitions:
   - `pending` -> `processing` -> `completed`
   - or `failed` (if generation failed)

Repeat this call until one terminal state is reached:
- `completed`: continue to Step 5
- `failed`: inspect `error` in response and stop

### Step 5: Retrieve the Generated Story
After status is `completed`:

1. Copy `story_id` from the completed job response.
2. Expand `GET /api/stories/{story_id}`.
3. Click **Try it out**.
4. Enter `story_id`.
5. Click **Execute**.

Validate response fields:
- `id`, `title`, `session_id`, `created_at`
- `root_node` (entry node)
- `all_nodes` (map of all generated nodes and options)

### Step 6: Functional Validation Checklist
A successful end-to-end Swagger test should confirm:

- Story job can be created with a theme.
- Job status endpoint eventually returns `completed`.
- Completed job contains non-null `story_id`.
- Story retrieval returns a complete branching structure:
  - Node content exists.
  - Ending flags (`is_ending`, `is_winning`) are present.
  - Options include text and next `node_id` references.

## Project Architecture
The app follows a layered FastAPI architecture:

1. API Layer (`routes/`):
   - Defines HTTP contracts and request handling.
   - Delegates persistence and generation logic.
   - Handles cookies, background tasks, and response mapping.

2. Schema Layer (`schemas/`):
   - Pydantic models for request/response validation.
   - Controls API payload shape.

3. Domain/Service Layer (`core/`):
   - Prompt templates and LLM schemas.
   - Story generation service (`StoryGenerator`) that:
     - Calls LLM via HTTP.
     - Validates generated JSON against strict Pydantic schema.
     - Persists story graph recursively.

4. Persistence Layer (`models/`, `db/`):
   - SQLAlchemy models for stories, nodes, and jobs.
   - DB session lifecycle and engine config.

5. App Bootstrap (`main.py`):
   - FastAPI app creation.
   - Middleware setup (CORS).
   - Router registration.
   - Startup table creation.

## Directory Structure

```text
.
┣ core
 ┃ ┣ __pycache__
 ┃ ┃ ┣ config.cpython-314.pyc
 ┃ ┃ ┣ models.cpython-314.pyc
 ┃ ┃ ┣ prompts.cpython-314.pyc
 ┃ ┃ ┣ story_generator.cpython-314.pyc
 ┃ ┃ ┗ __init__.cpython-314.pyc
 ┃ ┣ config.py
 ┃ ┣ models.py
 ┃ ┣ prompts.py
 ┃ ┣ story_generator.py
 ┃ ┗ __init__.py
 ┣ db
 ┃ ┣ __pycache__
 ┃ ┃ ┣ database.cpython-314.pyc
 ┃ ┃ ┗ __init__.cpython-314.pyc
 ┃ ┣ database.py
 ┃ ┗ __init__.py
 ┣ models
 ┃ ┣ __pycache__
 ┃ ┃ ┣ job.cpython-314.pyc
 ┃ ┃ ┣ story.cpython-314.pyc
 ┃ ┃ ┗ __init__.cpython-314.pyc
 ┃ ┣ job.py
 ┃ ┣ story.py
 ┃ ┗ __init__.py
 ┣ routes
 ┃ ┣ __pycache__
 ┃ ┃ ┣ job.cpython-314.pyc
 ┃ ┃ ┣ story.cpython-314.pyc
 ┃ ┃ ┗ __init__.cpython-314.pyc
 ┃ ┣ job.py
 ┃ ┣ story.py
 ┃ ┗ __init__.py
 ┣ schemas
 ┃ ┣ __pycache__
 ┃ ┃ ┣ job.cpython-314.pyc
 ┃ ┃ ┣ story.cpython-314.pyc
 ┃ ┃ ┗ __init__.cpython-314.pyc
 ┃ ┣ job.py
 ┃ ┣ story.py
 ┃ ┗ __init__.py
 ┣ __pycache__
 ┃ ┗ main.cpython-314.pyc
 ┣ .env
 ┣ .gitignore
 ┣ .python-version
 ┣ database.db
 ┣ main.py
 ┣ pyproject.toml
 ┣ README.md
 ┣ uv.lock
 ┗ __init__.py       
```

## Data Model Summary
- `stories` table:
  - One row per generated story session and title metadata.
- `story_nodes` table:
  - One row per story node.
  - Includes content, ending flags, and JSON options list.
- `story_jobs` table:
  - Async job tracking (`pending`, `processing`, `completed`, `failed`).
  - Stores `story_id` when done, and `error` when failed.



