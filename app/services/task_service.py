"""Business logic layer for task operations."""

from typing import Optional

from app.db.models import Task, Priority, Status
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
        self, task_data: TaskCreate, use_ai_priority: bool = False
    ) -> Task:
        """
        Create a new task with optional AI-based prioritization.
        
        Args:
            task_data: Task creation data
            use_ai_priority: Whether to use AI for priority suggestion
            
        Returns:
            Created task
        """
        priority = task_data.priority
        priority_reason = None

        if use_ai_priority:
            priority, priority_reason = await self.ai_service.suggest_priority(
                task_data.title, task_data.description
            )

        task = Task(
            title=task_data.title,
            description=task_data.description,
            priority=priority,
            priority_reason=priority_reason,
            status=task_data.status,
        )

        return self.repository.create(task)

    def get_task(self, task_id: int) -> Optional[Task]:
        """
        Get a task by ID.
        
        Args:
            task_id: Task identifier
            
        Returns:
            Task if found, None otherwise
        """
        return self.repository.get_by_id(task_id)

    def get_tasks(
        self,
        status: Optional[Status] = None,
        priority: Optional[Priority] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> list[Task]:
        """
        Get all tasks with optional filtering.
        
        Args:
            status: Optional status filter
            priority: Optional priority filter
            skip: Number of records to skip
            limit: Maximum number of records to return
            
        Returns:
            List of tasks
        """
        return self.repository.get_all(status=status, priority=priority, skip=skip, limit=limit)

    def update_task(self, task_id: int, task_data: TaskUpdate) -> Optional[Task]:
        """
        Update an existing task.
        
        Args:
            task_id: Task identifier
            task_data: Task update data
            
        Returns:
            Updated task if found, None otherwise
        """
        task = self.repository.get_by_id(task_id)
        if not task:
            return None

        update_data = task_data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(task, field, value)

        return self.repository.update(task)

    async def reanalyze_priority(self, task_id: int) -> Optional[Task]:
        """
        Re-analyze priority for an existing task using AI.
        
        Args:
            task_id: Task identifier
            
        Returns:
            Updated task if found, None otherwise
        """
        task = self.repository.get_by_id(task_id)
        if not task:
            return None

        priority, priority_reason = await self.ai_service.suggest_priority(
            task.title, task.description
        )

        update_data = TaskUpdate(priority=priority, priority_reason=priority_reason)
        return self.update_task(task_id, update_data)

    def delete_task(self, task_id: int) -> bool:
        """
        Delete a task by ID.
        
        Args:
            task_id: Task identifier
            
        Returns:
            True if deleted, False if not found
        """
        return self.repository.delete(task_id)

