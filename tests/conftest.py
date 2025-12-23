"""Pytest configuration and fixtures."""

import pytest
from fastapi.testclient import TestClient
from sqlmodel import SQLModel, create_engine, Session

from app.main import app
from app.db.models import Task


@pytest.fixture(scope="function")
def test_engine():
    """Create a test database engine for each test."""
    # Use file-based SQLite for better thread safety with FastAPI TestClient
    # Use check_same_thread=False for SQLite to work with FastAPI TestClient
    engine = create_engine(
        "sqlite:///./test_todo.db",
        connect_args={"check_same_thread": False},
        echo=False,
    )
    # Create all tables
    SQLModel.metadata.create_all(engine)
    yield engine
    # Clean up: drop tables and close connections
    SQLModel.metadata.drop_all(engine)
    engine.dispose()


@pytest.fixture(scope="function")
def test_db(test_engine):
    """Create a test database session for each test."""
    with Session(test_engine) as session:
        yield session


@pytest.fixture(scope="function")
def client(test_engine):
    """Create a test client with test database dependency override."""
    # Override the get_session dependency to create a new session per request
    from app.db.session import get_session
    
    def override_get_session():
        with Session(test_engine) as session:
            yield session
    
    app.dependency_overrides[get_session] = override_get_session
    
    with TestClient(app) as test_client:
        yield test_client
    
    app.dependency_overrides.clear()

