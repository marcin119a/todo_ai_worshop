"""FastAPI application entry point."""

from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.routers import tasks
from app.db.session import create_db_and_tables


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifespan events."""
    # Startup
    create_db_and_tables()
    yield
    # Shutdown (if needed)


app = FastAPI(
    title="TODO API",
    description="MVP TODO application with AI prioritization",
    version="0.1.0",
    lifespan=lifespan,
)

app.include_router(tasks.router)


@app.get("/")
def root() -> dict[str, str]:
    """Root endpoint."""
    return {"message": "TODO API", "version": "0.1.0"}


@app.get("/health")
def health() -> dict[str, str]:
    """Health check endpoint."""
    return {"status": "healthy"}

