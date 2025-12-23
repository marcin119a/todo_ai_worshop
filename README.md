# TODO API - MVP Application

A production-ready MVP TODO application built with FastAPI, featuring clean architecture, AI-powered task prioritization, and comprehensive testing.

## Features

- **CRUD Operations**: Full Create, Read, Update, Delete functionality for tasks
- **AI Prioritization**: Optional OpenAI integration for intelligent task prioritization with natural language explanations
- **Priority Explanations**: Transparent AI decisions with detailed explanations including key factors and keywords
- **Clean Architecture**: Clear separation between API, Service, and Repository layers
- **Type Safety**: Full type hints and Pydantic v2 validation
- **Database Migrations**: Alembic for version-controlled database schema changes
- **Comprehensive Testing**: pytest test suite with FastAPI TestClient

## Tech Stack

- **FastAPI** (latest stable) - Modern, fast web framework
- **Pydantic v2** - Data validation and settings management
- **SQLModel** - SQL database ORM built on SQLAlchemy
- **SQLite** - Lightweight database (easily replaceable)
- **Alembic** - Database migration tool
- **pytest** - Testing framework
- **OpenAI API** - AI-powered task prioritization (optional)

## Project Structure

```
todo_ai_worshop/
├── app/
│   ├── __init__.py
│   ├── main.py                 # FastAPI application entry point
│   ├── api/
│   │   ├── __init__.py
│   │   └── routers/
│   │       ├── __init__.py
│   │       └── tasks.py        # Task API endpoints
│   ├── core/
│   │   ├── __init__.py
│   │   └── config.py           # Application configuration
│   ├── db/
│   │   ├── __init__.py
│   │   ├── models.py           # SQLModel database models
│   │   ├── repository.py       # Repository layer for database operations
│   │   └── session.py          # Database session management
│   ├── schemas/
│   │   ├── __init__.py
│   │   └── task.py             # Pydantic schemas for API
│   └── services/
│       ├── __init__.py
│       ├── ai_priority_service.py  # AI prioritization service
│       └── task_service.py         # Business logic layer
├── migrations/                 # Alembic database migrations
│   ├── env.py
│   ├── script.py.mako
│   └── versions/
├── tests/
│   ├── __init__.py
│   ├── conftest.py            # pytest fixtures
│   └── test_tasks_api.py      # API endpoint tests
├── alembic.ini                 # Alembic configuration
├── pyproject.toml              # Project dependencies and config
├── requirements.txt            # Python dependencies
└── README.md                   # This file
```

## Installation

1. **Clone the repository** (if applicable) or navigate to the project directory

2. **Create a virtual environment**:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. **Install dependencies**:
```bash
pip install -r requirements.txt
```

4. **Set up environment variables** (optional):
```bash
cp .env.example .env
# Edit .env and add your OPENAI_API_KEY if you want AI prioritization
```

5. **Run database migrations**:
```bash
alembic upgrade head
```

## Running the Application

Start the FastAPI development server:

```bash
uvicorn app.main:app --reload
```

The API will be available at:
- **API**: http://localhost:8000
- **Interactive API Docs**: http://localhost:8000/docs
- **Alternative API Docs**: http://localhost:8000/redoc

## API Endpoints

### Tasks

- `POST /tasks/` - Create a new task
  - Query parameter: `use_ai_priority` (boolean) - Use AI for priority suggestion
- `POST /tasks/priority/analyze` - Analyze task content and suggest priority (without creating task)
- `GET /tasks/` - Get all tasks (with optional filters)
  - Query parameters: `status`, `priority`, `skip`, `limit`
- `GET /tasks/{task_id}` - Get a specific task by ID
- `PATCH /tasks/{task_id}` - Update a task
- `POST /tasks/{task_id}/reanalyze-priority` - Re-analyze and update priority for an existing task using AI
- `DELETE /tasks/{task_id}` - Delete a task

### Health & Info

- `GET /` - Root endpoint
- `GET /health` - Health check endpoint

## Task Model

Tasks have the following fields:

- `id` (int) - Auto-generated unique identifier
- `title` (str, max 200 chars) - Task title
- `description` (str, optional, max 1000 chars) - Task description
- `priority` (enum) - Priority level: `low`, `medium`, `high`
- `priority_reason` (str, optional, max 500 chars) - Natural language explanation of why the task received its priority (set by AI, includes key factors and keywords)
- `status` (enum) - Task status: `todo`, `done`
- `created_at` (datetime) - Creation timestamp
- `updated_at` (datetime) - Last update timestamp

## Example Usage

### Create a Task

```bash
curl -X POST "http://localhost:8000/tasks/" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Complete project documentation",
    "description": "Write comprehensive README and API docs",
    "priority": "high",
    "status": "todo"
  }'
```

### Create a Task with AI Prioritization

```bash
curl -X POST "http://localhost:8000/tasks/?use_ai_priority=true" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Fix critical bug in production",
    "description": "Users cannot log in, urgent fix needed"
  }'
```

### Get All Tasks

```bash
curl "http://localhost:8000/tasks/"
```

### Get Tasks by Status

```bash
curl "http://localhost:8000/tasks/?status=done"
```

### Update a Task

```bash
curl -X PATCH "http://localhost:8000/tasks/1" \
  -H "Content-Type: application/json" \
  -d '{
    "status": "done"
  }'
```

### Analyze Priority Without Creating Task

```bash
curl -X POST "http://localhost:8000/tasks/priority/analyze" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Fix critical bug in production",
    "description": "Users cannot log in, urgent fix needed"
  }'
```

### Re-analyze Priority for Existing Task

```bash
curl -X POST "http://localhost:8000/tasks/1/reanalyze-priority"
```

### Delete a Task

```bash
curl -X DELETE "http://localhost:8000/tasks/1"
```

## Testing

Run the test suite:

```bash
pytest
```

Run tests with coverage:

```bash
pytest --cov=app --cov-report=html
```

## Database Migrations

Create a new migration:

```bash
alembic revision --autogenerate -m "Description of changes"
```

Apply migrations:

```bash
alembic upgrade head
```

Rollback last migration:

```bash
alembic downgrade -1
```

## Architecture

The application follows clean architecture principles:

1. **API Layer** (`app/api/routers/`) - HTTP endpoints, request/response handling
2. **Service Layer** (`app/services/`) - Business logic, orchestration
3. **Repository Layer** (`app/db/repository.py`) - Database operations abstraction
4. **Models** (`app/db/models.py`) - Database schema definitions
5. **Schemas** (`app/schemas/`) - Pydantic models for API validation

### Dependency Injection

FastAPI's dependency injection system is used throughout:
- Database sessions are injected into repositories
- Repositories are injected into services
- Services are injected into route handlers

### AI Service Abstraction

The AI prioritization is abstracted behind a protocol interface, allowing easy swapping of implementations:
- `OpenAIPriorityService` - Real OpenAI integration
- `MockAIPriorityService` - Fallback with simple heuristics

## Development

### Code Quality

The project uses:
- **ruff** - Fast Python linter
- **black** - Code formatter

Format code:

```bash
black app tests
```

Lint code:

```bash
ruff check app tests
```

### Type Checking

All code includes type hints. Consider using `mypy` for static type checking:

```bash
pip install mypy
mypy app
```

## Configuration

Configuration is managed through environment variables (see `.env.example`):

- `DATABASE_URL` - Database connection string (default: `sqlite:///./todo.db`)
- `OPENAI_API_KEY` - OpenAI API key for AI prioritization (optional)

## License

This is an MVP project for demonstration purposes.

## Next Steps (Future Enhancements)

- User authentication and authorization
- Task categories/tags
- Task due dates and reminders
- Task dependencies
- Bulk operations
- Advanced filtering and search
- Task history/audit log
- WebSocket support for real-time updates
- Background task processing with Celery
- Docker containerization
- CI/CD pipeline

