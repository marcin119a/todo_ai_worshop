"""API routes for task operations."""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import Session

from app.api.deps import get_current_admin_user, get_current_user
from app.core.config import settings
from app.db.models import Priority, Status, User
from app.db.repository import TaskRepository
from app.db.session import get_session
from app.schemas.task import (
    PriorityAnalysisRequest,
    PriorityAnalysisResponse,
    TaskCreate,
    TaskResponse,
    TaskUpdate,
)
from app.services.ai_priority_service import MockAIPriorityService, OpenAIPriorityService
from app.services.task_service import TaskService

router = APIRouter(prefix="/tasks", tags=["tasks"])


def get_task_repository(session: Session = Depends(get_session)) -> TaskRepository:
    """Dependency to get task repository."""
    return TaskRepository(session)


def get_ai_service() -> MockAIPriorityService | OpenAIPriorityService:
    """Dependency to get AI priority service."""
    if settings.openai_api_key:
        return OpenAIPriorityService(settings.openai_api_key)
    return MockAIPriorityService()


def get_task_service(
    repository: TaskRepository = Depends(get_task_repository),
    ai_service: MockAIPriorityService | OpenAIPriorityService = Depends(get_ai_service),
) -> TaskService:
    """Dependency to get task service."""
    return TaskService(repository, ai_service)


@router.post("/", response_model=TaskResponse, status_code=201)
async def create_task(
    task_data: TaskCreate,
    use_ai_priority: bool = Query(default=False, description="Use AI for priority suggestion"),
    service: TaskService = Depends(get_task_service),
    current_user: User = Depends(get_current_user),
) -> TaskResponse:
    """
    Create a new task for the authenticated user.

    Args:
        task_data: Task creation data
        use_ai_priority: Whether to use AI for priority suggestion
        service: Task service dependency
        current_user: Authenticated user

    Returns:
        Created task
    """
    task = await service.create_task(task_data, use_ai_priority=use_ai_priority, owner_id=current_user.id)
    return TaskResponse.model_validate(task)


@router.post("/priority/analyze", response_model=PriorityAnalysisResponse)
async def analyze_priority(
    payload: PriorityAnalysisRequest,
    ai_service: MockAIPriorityService | OpenAIPriorityService = Depends(get_ai_service),
    _: User = Depends(get_current_user),
) -> PriorityAnalysisResponse:
    """
    Analyze task content and suggest a priority without creating a task.

    Args:
        payload: Task title and optional description for analysis
        ai_service: AI priority service dependency

    Returns:
        Suggested priority and analysis reason
    """
    priority, reason = await ai_service.suggest_priority(payload.title, payload.description)
    return PriorityAnalysisResponse(priority=priority, priority_reason=reason)


@router.get("/", response_model=list[TaskResponse])
def get_tasks(
    status: Optional[Status] = Query(default=None, description="Filter by status"),
    priority: Optional[Priority] = Query(default=None, description="Filter by priority"),
    skip: int = Query(default=0, ge=0, description="Number of records to skip"),
    limit: int = Query(default=100, ge=1, le=1000, description="Maximum number of records"),
    service: TaskService = Depends(get_task_service),
    current_user: User = Depends(get_current_user),
) -> list[TaskResponse]:
    """
    Get the authenticated user's tasks with optional filtering.

    Args:
        status: Optional status filter
        priority: Optional priority filter
        skip: Number of records to skip
        limit: Maximum number of records
        service: Task service dependency
        current_user: Authenticated user

    Returns:
        List of tasks belonging to the current user
    """
    tasks = service.get_tasks(
        status=status, priority=priority, skip=skip, limit=limit, owner_id=current_user.id
    )
    return [TaskResponse.model_validate(task) for task in tasks]


@router.get("/admin/all", response_model=list[TaskResponse])
def admin_get_all_tasks(
    status: Optional[Status] = Query(default=None),
    priority: Optional[Priority] = Query(default=None),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=1000),
    service: TaskService = Depends(get_task_service),
    _: User = Depends(get_current_admin_user),
) -> list[TaskResponse]:
    """
    Admin: get all tasks across all users.

    Args:
        status: Optional status filter
        priority: Optional priority filter
        skip: Number of records to skip
        limit: Maximum number of records
        service: Task service dependency

    Returns:
        All tasks (unscoped)
    """
    tasks = service.get_tasks(status=status, priority=priority, skip=skip, limit=limit)
    return [TaskResponse.model_validate(task) for task in tasks]


@router.get("/admin/stats", response_model=dict)
def admin_get_stats(
    service: TaskService = Depends(get_task_service),
    _: User = Depends(get_current_admin_user),
) -> dict:
    """
    Admin: get task statistics across all users.

    Returns:
        Counts per status and priority
    """
    all_tasks = service.get_tasks(limit=10000)
    return {
        "total": len(all_tasks),
        "by_status": {
            s.value: sum(1 for t in all_tasks if t.status == s) for s in Status
        },
        "by_priority": {
            p.value: sum(1 for t in all_tasks if t.priority == p) for p in Priority
        },
    }


@router.get("/{task_id}", response_model=TaskResponse)
def get_task(
    task_id: int,
    service: TaskService = Depends(get_task_service),
    current_user: User = Depends(get_current_user),
) -> TaskResponse:
    """
    Get a task by ID (must belong to the authenticated user).

    Args:
        task_id: Task identifier
        service: Task service dependency
        current_user: Authenticated user

    Returns:
        Task details

    Raises:
        HTTPException: If task not found or not owned by current user
    """
    task = service.get_task(task_id, owner_id=current_user.id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return TaskResponse.model_validate(task)


@router.patch("/{task_id}", response_model=TaskResponse)
async def update_task(
    task_id: int,
    task_data: TaskUpdate,
    service: TaskService = Depends(get_task_service),
    current_user: User = Depends(get_current_user),
) -> TaskResponse:
    """
    Update an existing task (must belong to the authenticated user).

    Args:
        task_id: Task identifier
        task_data: Task update data
        service: Task service dependency
        current_user: Authenticated user

    Returns:
        Updated task

    Raises:
        HTTPException: If task not found or not owned by current user
    """
    task = service.update_task(task_id, task_data, owner_id=current_user.id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return TaskResponse.model_validate(task)


@router.post("/{task_id}/reanalyze-priority", response_model=TaskResponse)
async def reanalyze_task_priority(
    task_id: int,
    service: TaskService = Depends(get_task_service),
    current_user: User = Depends(get_current_user),
) -> TaskResponse:
    """
    Re-analyze and update priority for an existing task using AI.

    Args:
        task_id: Task identifier
        service: Task service dependency
        current_user: Authenticated user

    Returns:
        Updated task with new priority and reason

    Raises:
        HTTPException: If task not found or not owned by current user
    """
    updated_task = await service.reanalyze_priority(task_id, owner_id=current_user.id)
    if not updated_task:
        raise HTTPException(status_code=404, detail="Task not found")
    return TaskResponse.model_validate(updated_task)


@router.delete("/{task_id}", status_code=204)
def delete_task(
    task_id: int,
    service: TaskService = Depends(get_task_service),
    current_user: User = Depends(get_current_user),
) -> None:
    """
    Delete a task by ID (must belong to the authenticated user).

    Args:
        task_id: Task identifier
        service: Task service dependency
        current_user: Authenticated user

    Raises:
        HTTPException: If task not found or not owned by current user
    """
    deleted = service.delete_task(task_id, owner_id=current_user.id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Task not found")
