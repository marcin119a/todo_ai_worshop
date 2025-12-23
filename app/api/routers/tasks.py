"""API routes for task operations."""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import Session

from app.core.config import settings
from app.db.models import Priority, Status
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
) -> TaskResponse:
    """
    Create a new task.

    Args:
        task_data: Task creation data
        use_ai_priority: Whether to use AI for priority suggestion
        service: Task service dependency

    Returns:
        Created task
    """
    task = await service.create_task(task_data, use_ai_priority=use_ai_priority)
    return TaskResponse.model_validate(task)


@router.post("/priority/analyze", response_model=PriorityAnalysisResponse)
async def analyze_priority(
    payload: PriorityAnalysisRequest,
    ai_service: MockAIPriorityService | OpenAIPriorityService = Depends(get_ai_service),
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
) -> list[TaskResponse]:
    """
    Get all tasks with optional filtering.

    Args:
        status: Optional status filter
        priority: Optional priority filter
        skip: Number of records to skip
        limit: Maximum number of records
        service: Task service dependency

    Returns:
        List of tasks
    """
    tasks = service.get_tasks(status=status, priority=priority, skip=skip, limit=limit)
    return [TaskResponse.model_validate(task) for task in tasks]


@router.get("/{task_id}", response_model=TaskResponse)
def get_task(
    task_id: int,
    service: TaskService = Depends(get_task_service),
) -> TaskResponse:
    """
    Get a task by ID.

    Args:
        task_id: Task identifier
        service: Task service dependency

    Returns:
        Task details

    Raises:
        HTTPException: If task not found
    """
    task = service.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return TaskResponse.model_validate(task)


@router.patch("/{task_id}", response_model=TaskResponse)
async def update_task(
    task_id: int,
    task_data: TaskUpdate,
    service: TaskService = Depends(get_task_service),
) -> TaskResponse:
    """
    Update an existing task.

    Args:
        task_id: Task identifier
        task_data: Task update data
        service: Task service dependency

    Returns:
        Updated task

    Raises:
        HTTPException: If task not found
    """
    task = service.update_task(task_id, task_data)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return TaskResponse.model_validate(task)


@router.post("/{task_id}/reanalyze-priority", response_model=TaskResponse)
async def reanalyze_task_priority(
    task_id: int,
    service: TaskService = Depends(get_task_service),
) -> TaskResponse:
    """
    Re-analyze and update priority for an existing task using AI.

    Args:
        task_id: Task identifier
        service: Task service dependency

    Returns:
        Updated task with new priority and reason

    Raises:
        HTTPException: If task not found
    """
    updated_task = await service.reanalyze_priority(task_id)
    if not updated_task:
        raise HTTPException(status_code=404, detail="Task not found")
    return TaskResponse.model_validate(updated_task)


@router.delete("/{task_id}", status_code=204)
def delete_task(
    task_id: int,
    service: TaskService = Depends(get_task_service),
) -> None:
    """
    Delete a task by ID.

    Args:
        task_id: Task identifier
        service: Task service dependency

    Raises:
        HTTPException: If task not found
    """
    deleted = service.delete_task(task_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Task not found")

