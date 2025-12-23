"""Repository layer for database operations."""

from typing import Optional

from sqlmodel import Session, select

from app.db.models import Task, Priority, Status


class TaskRepository:
    """Repository for task database operations."""

    def __init__(self, session: Session) -> None:
        """Initialize repository with database session."""
        self.session = session

    def create(self, task: Task) -> Task:
        """Create a new task."""
        self.session.add(task)
        self.session.commit()
        self.session.refresh(task)
        return task

    def get_by_id(self, task_id: int) -> Optional[Task]:
        """Get a task by ID."""
        return self.session.get(Task, task_id)

    def get_all(
        self,
        status: Optional[Status] = None,
        priority: Optional[Priority] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> list[Task]:
        """Get all tasks with optional filtering."""
        statement = select(Task)
        
        if status:
            statement = statement.where(Task.status == status)
        if priority:
            statement = statement.where(Task.priority == priority)
        
        statement = statement.offset(skip).limit(limit)
        return list(self.session.exec(statement).all())

    def update(self, task: Task) -> Task:
        """Update an existing task."""
        from datetime import datetime, timezone
        task.updated_at = datetime.now(timezone.utc)
        self.session.add(task)
        self.session.commit()
        self.session.refresh(task)
        return task

    def delete(self, task_id: int) -> bool:
        """Delete a task by ID."""
        task = self.get_by_id(task_id)
        if task:
            self.session.delete(task)
            self.session.commit()
            return True
        return False

