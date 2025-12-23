"""Database session management."""

from sqlmodel import SQLModel, create_engine, Session

from app.core.config import settings

engine = create_engine(
    settings.database_url,
    connect_args={"check_same_thread": False} if "sqlite" in settings.database_url else {},
    echo=False,
)


def get_session() -> Session:
    """Create and yield a database session."""
    with Session(engine) as session:
        yield session


def create_db_and_tables() -> None:
    """Create database tables."""
    SQLModel.metadata.create_all(engine)

