"""Business logic layer for task operations."""

from typing import Optional

from app.db.models import Priority, Status, Task
from app.db.repository import TaskRepository
from app.schemas.task import TaskCreate, TaskUpdate
from app.services.ai_priority_service import AIPriorityService, MockAIPriorityService


class TaskService:
    """Service layer for task business logic."""

    def __init__(
        self,
        repository: TaskRepository,
        ai_service: Optional[AIPriorityService] = None,
    ) -> None:
        """Initialize task service with repository and optional AI service."""
        self.repository = repository
        self.ai_service = ai_service or MockAIPriorityService()

    async def create_task(
        self, task_data: TaskCreate, use_ai_priority: bool = False, owner_id: Optional[int] = None
    ) -> Task:
        """
        Create a new task with optional AI-based prioritization.

        Args:
            task_data: Task creation data
            use_ai_priority: Whether to use AI for priority suggestion
            owner_id: ID of the owning user

        Returns:
            Created task
        """
        priority = task_data.priority
        priority_reason = None

        # Always get AI suggestion to check for important cases (e.g., exams)
        ai_priority, priority_reason = await self.ai_service.suggest_priority(
            task_data.title, task_data.description
        )

        if use_ai_priority:
            priority = ai_priority
        elif ai_priority == Priority.HIGH:
            # Auto-override to HIGH if AI detects high-priority case
            priority = ai_priority

        task = Task(
            title=task_data.title,
            description=task_data.description,
            priority=priority,
            priority_reason=priority_reason,
            status=task_data.status,
            owner_id=owner_id,
        )

        return self.repository.create(task)

    def get_task(self, task_id: int, owner_id: Optional[int] = None) -> Optional[Task]:
        """
        Get a task by ID, scoped to owner if provided.

        Args:
            task_id: Task identifier
            owner_id: If set, only return the task if it belongs to this user

        Returns:
            Task if found and accessible, None otherwise
        """
        return self.repository.get_by_id(task_id, owner_id=owner_id)

    def get_tasks(
        self,
        status: Optional[Status] = None,
        priority: Optional[Priority] = None,
        skip: int = 0,
        limit: int = 100,
        owner_id: Optional[int] = None,
    ) -> list[Task]:
        """
        Get tasks with optional filtering, scoped to owner if provided.

        Args:
            status: Optional status filter
            priority: Optional priority filter
            skip: Number of records to skip
            limit: Maximum number of records to return
            owner_id: If set, only return tasks belonging to this user

        Returns:
            List of tasks
        """
        return self.repository.get_all(
            status=status, priority=priority, skip=skip, limit=limit, owner_id=owner_id
        )

    def update_task(
        self, task_id: int, task_data: TaskUpdate, owner_id: Optional[int] = None
    ) -> Optional[Task]:
        """
        Update an existing task.

        Args:
            task_id: Task identifier
            task_data: Task update data
            owner_id: If set, only update the task if it belongs to this user

        Returns:
            Updated task if found and accessible, None otherwise
        """
        task = self.repository.get_by_id(task_id, owner_id=owner_id)
        if not task:
            return None

        update_data = task_data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(task, field, value)

        return self.repository.update(task)

    async def reanalyze_priority(
        self, task_id: int, owner_id: Optional[int] = None
    ) -> Optional[Task]:
        """
        Re-analyze priority for an existing task using AI.

        Args:
            task_id: Task identifier
            owner_id: If set, only process the task if it belongs to this user

        Returns:
            Updated task if found and accessible, None otherwise
        """
        task = self.repository.get_by_id(task_id, owner_id=owner_id)
        if not task:
            return None

        priority, priority_reason = await self.ai_service.suggest_priority(
            task.title, task.description
        )

        update_data = TaskUpdate(priority=priority, priority_reason=priority_reason)
        return self.update_task(task_id, update_data, owner_id=owner_id)

    def get_stats(self) -> dict:
        """Return task counts grouped by status and priority."""
        status_counts = dict(self.repository.count_by_status())
        priority_counts = dict(self.repository.count_by_priority())
        return {
            "total": self.repository.count_total(),
            "by_status": {s.value: status_counts.get(s, 0) for s in Status},
            "by_priority": {p.value: priority_counts.get(p, 0) for p in Priority},
        }

    def delete_task(self, task_id: int, owner_id: Optional[int] = None) -> bool:
        """
        Delete a task by ID.

        Args:
            task_id: Task identifier
            owner_id: If set, only delete the task if it belongs to this user

        Returns:
            True if deleted, False if not found or not accessible
        """
        return self.repository.delete(task_id, owner_id=owner_id)
