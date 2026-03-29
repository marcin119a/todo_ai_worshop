# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository. Prefer minimal, incremental changes over rewrites.


## Commands

```bash
# Install dependencies
pip install -r requirements.txt

# Run dev server
uvicorn app.main:app --reload

# Run tests
pytest
pytest --cov=app --cov-report=html   # with coverage
pytest tests/test_tasks_api.py::test_create_task  # single test

# Lint and format
ruff check app tests
black app tests

# Database migrations
alembic upgrade head
alembic revision --autogenerate -m "Description"
alembic downgrade -1
```

## Architecture

Clean layered architecture — no layer should skip the one below it:

```
API Layer       app/api/routers/tasks.py       HTTP request/response handling
Service Layer   app/services/task_service.py   Business logic, orchestration
Repository      app/db/repository.py           All database queries
Models          app/db/models.py               SQLModel ORM definitions
Schemas         app/schemas/task.py            Pydantic models for API I/O
Config          app/core/config.py             Settings via Pydantic BaseSettings
```

FastAPI's dependency injection chain: `get_session → get_task_repository → get_ai_service → get_task_service` — route handlers receive fully composed services.

## AI Prioritization

`app/services/ai_priority_service.py` defines a `AIPriorityService` Protocol with two implementations:

- `OpenAIPriorityService` — calls GPT-3.5-turbo; uses in-memory caching
- `MockAIPriorityService` — heuristic fallback using keyword matching (Polish + English)

The mock is always used in tests (via dependency override in `conftest.py`). The real service activates only when `OPENAI_API_KEY` is set. AI can override user-set priority for detected critical cases (urgent/exam keywords).

## Testing

Tests use dependency overrides to replace the AI service with `MockAIPriorityService` and use a file-based SQLite test database (not in-memory) for thread safety with FastAPI `TestClient`. Fixtures are function-scoped, so each test gets a fresh DB.

Use **pytest-mock** (`mocker` fixture) for all mocking — never `unittest.mock.patch` directly. Key conventions:
- `mocker.patch(...)` — auto-reverts after each test, no `with` block needed
- `mocker.MagicMock()` — for constructing fake objects
- Module-level globals (e.g. `_PRIORITY_CACHE`) must be cleared in an `autouse` fixture when testing modules that use them

## Key Conventions (from .cursorrules)

- `async def` for all endpoints
- Early returns / guard clauses — happy path last
- No unused imports or dead code
- Descriptive variable names with auxiliary verbs (`is_active`, `has_permission`)
- All endpoints documented with Google-style docstrings
- AI calls isolated in the service layer; never block core functionality on AI failure
- `use_ai_priority` query param on `POST /tasks/` controls whether AI prioritizes the task
