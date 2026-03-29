"""Repository layer for database operations."""

from datetime import date
from typing import Optional

from sqlalchemy import func, text
from sqlmodel import Session, select

from app.db.models import Category, Priority, Status, Task, User


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


class CategoryRepository:
    """Repository for category database operations."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def create(self, category: Category) -> Category:
        self.session.add(category)
        self.session.commit()
        self.session.refresh(category)
        return category

    def get_by_id(self, category_id: int) -> Optional[Category]:
        return self.session.get(Category, category_id)

    def get_by_name(self, name: str) -> Optional[Category]:
        return self.session.exec(select(Category).where(Category.name == name)).first()

    def delete_and_nullify_tasks(self, category_id: int) -> bool:
        category = self.get_by_id(category_id)
        if not category:
            return False
        tasks = list(self.session.exec(select(Task).where(Task.category_id == category_id)).all())
        for task in tasks:
            task.category_id = None
            self.session.add(task)
        self.session.delete(category)
        self.session.commit()
        return True


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

    def get_category(self, category_id: int) -> Optional[Category]:
        """Get a category by ID."""
        return self.session.get(Category, category_id)

    def get_all(
        self,
        status: Optional[Status] = None,
        priority: Optional[Priority] = None,
        skip: int = 0,
        limit: int = 100,
        owner_id: Optional[int] = None,
        category_id: Optional[int] = None,
        tag: Optional[str] = None,
        overdue: bool = False,
    ) -> list[Task]:
        """Get all tasks with optional filtering."""
        statement = select(Task)

        if owner_id is not None:
            statement = statement.where(Task.owner_id == owner_id)
        if status:
            statement = statement.where(Task.status == status)
        if priority:
            statement = statement.where(Task.priority == priority)
        if category_id is not None:
            statement = statement.where(Task.category_id == category_id)
        if tag is not None:
            statement = statement.where(
                text("EXISTS (SELECT 1 FROM json_each(task.tags) WHERE value = :tag_val)").bindparams(tag_val=tag)
            )
        if overdue:
            today = date.today()
            statement = statement.where(Task.due_date < today).where(Task.status != Status.DONE)

        statement = statement.offset(skip).limit(limit)
        return list(self.session.exec(statement).all())

    def get_upcoming(
        self,
        days: int,
        owner_id: Optional[int] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> list[Task]:
        """Get tasks due within the next `days` days (not yet done)."""
        today = date.today()
        from datetime import timedelta
        cutoff = today + timedelta(days=days)
        statement = (
            select(Task)
            .where(Task.due_date >= today)
            .where(Task.due_date <= cutoff)
            .where(Task.status != Status.DONE)
        )
        if owner_id is not None:
            statement = statement.where(Task.owner_id == owner_id)
        statement = statement.order_by(Task.due_date).offset(skip).limit(limit)
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
