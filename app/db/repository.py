"""Repository layer for database operations."""

from typing import Optional

from sqlalchemy import func
from sqlmodel import Session, select

from app.db.models import Priority, Status, Task, User


class UserRepository:
    """Repository for user database operations."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def create(self, user: User) -> User:
        self.session.add(user)
        self.session.commit()
        self.session.refresh(user)
        return user

    def get_by_id(self, user_id: int) -> Optional[User]:
        return self.session.get(User, user_id)

    def get_by_email(self, email: str) -> Optional[User]:
        return self.session.exec(select(User).where(User.email == email)).first()


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

    def get_by_id(self, task_id: int, owner_id: Optional[int] = None) -> Optional[Task]:
        """Get a task by ID, optionally scoped to an owner."""
        task = self.session.get(Task, task_id)
        if task is None:
            return None
        if owner_id is not None and task.owner_id != owner_id:
            return None
        return task

    def get_all(
        self,
        status: Optional[Status] = None,
        priority: Optional[Priority] = None,
        skip: int = 0,
        limit: int = 100,
        owner_id: Optional[int] = None,
    ) -> list[Task]:
        """Get all tasks with optional filtering."""
        statement = select(Task)

        if owner_id is not None:
            statement = statement.where(Task.owner_id == owner_id)
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

    def count_total(self) -> int:
        """Return total number of tasks."""
        return self.session.exec(select(func.count(Task.id))).one()

    def count_by_status(self) -> list[tuple]:
        """Return list of (status, count) tuples."""
        return self.session.exec(
            select(Task.status, func.count(Task.id)).group_by(Task.status)
        ).all()

    def count_by_priority(self) -> list[tuple]:
        """Return list of (priority, count) tuples."""
        return self.session.exec(
            select(Task.priority, func.count(Task.id)).group_by(Task.priority)
        ).all()

    def delete(self, task_id: int, owner_id: Optional[int] = None) -> bool:
        """Delete a task by ID, optionally scoped to an owner."""
        task = self.get_by_id(task_id, owner_id=owner_id)
        if task:
            self.session.delete(task)
            self.session.commit()
            return True
        return False
