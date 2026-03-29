"""API routes for task operations."""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import Session

from app.api.deps import get_current_admin_user, get_current_user
from app.core.config import settings
from app.db.models import Category, Priority, Status, User
from app.db.repository import CategoryRepository, TaskRepository
from app.db.session import get_session
from app.schemas.task import (
    PriorityAnalysisRequest,
    PriorityAnalysisResponse,
    TagCreate,
    TaskCreate,
    TaskResponse,
    TaskUpdate,
)
from app.services.ai_priority_service import MockAIPriorityService, OpenAIPriorityService
from app.services.task_service import TaskService

router = APIRouter(prefix="/tasks", tags=["tasks"])


class TaskListParams:
    """Common query parameters for task listing endpoints."""

    def __init__(
        self,
        status: Optional[Status] = Query(default=None, description="Filter by status"),
        priority: Optional[Priority] = Query(default=None, description="Filter by priority"),
        category_id: Optional[int] = Query(default=None, description="Filter by category ID"),
        tag: Optional[str] = Query(default=None, description="Filter by tag"),
        overdue: bool = Query(default=False, description="Return only overdue tasks (past due_date, not done)"),
        skip: int = Query(default=0, ge=0, description="Number of records to skip"),
        limit: int = Query(default=100, ge=1, le=1000, description="Maximum number of records"),
    ):
        self.status = status
        self.priority = priority
        self.category_id = category_id
        self.tag = tag
        self.overdue = overdue
        self.skip = skip
        self.limit = limit


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


def _get_category_name(category_id: Optional[int], session: Session) -> Optional[str]:
    """Resolve category name from ID."""
    if not category_id:
        return None
    category = session.get(Category, category_id)
    return category.name if category else None


@router.post("/", response_model=TaskResponse, status_code=201)
async def create_task(
    task_data: TaskCreate,
    use_ai_priority: bool = Query(default=False, description="Use AI for priority suggestion"),
    service: TaskService = Depends(get_task_service),
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> TaskResponse:
    """
    Create a new task for the authenticated user.

    Args:
        task_data: Task creation data
        use_ai_priority: Whether to use AI for priority suggestion
        service: Task service dependency
        session: Database session
        current_user: Authenticated user

    Returns:
        Created task

    Raises:
        HTTPException: 404 if category_id does not exist
    """
    if task_data.category_id is not None:
        category = session.get(Category, task_data.category_id)
        if not category:
            raise HTTPException(status_code=404, detail="Category not found")
        category_name = category.name
    else:
        category_name = None

    task = await service.create_task(
        task_data,
        use_ai_priority=use_ai_priority,
        owner_id=current_user.id,
        category_name=category_name,
    )
    return service.to_response(task)


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
    params: TaskListParams = Depends(),
    service: TaskService = Depends(get_task_service),
    current_user: User = Depends(get_current_user),
) -> list[TaskResponse]:
    """
    Get the authenticated user's tasks with optional filtering.

    Args:
        params: Filter and pagination parameters
        service: Task service dependency
        current_user: Authenticated user

    Returns:
        List of tasks belonging to the current user
    """
    tasks = service.get_tasks(
        status=params.status,
        priority=params.priority,
        skip=params.skip,
        limit=params.limit,
        owner_id=current_user.id,
        category_id=params.category_id,
        tag=params.tag,
        overdue=params.overdue,
    )
    return [service.to_response(task) for task in tasks]


@router.get("/admin/all", response_model=list[TaskResponse])
def admin_get_all_tasks(
    params: TaskListParams = Depends(),
    service: TaskService = Depends(get_task_service),
    _: User = Depends(get_current_admin_user),
) -> list[TaskResponse]:
    """
    Admin: get all tasks across all users.

    Args:
        params: Filter and pagination parameters
        service: Task service dependency

    Returns:
        All tasks (unscoped)
    """
    tasks = service.get_tasks(
        status=params.status,
        priority=params.priority,
        skip=params.skip,
        limit=params.limit,
        category_id=params.category_id,
        tag=params.tag,
        overdue=params.overdue,
    )
    return [service.to_response(task) for task in tasks]


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
    return service.get_stats()


@router.get("/upcoming", response_model=list[TaskResponse])
def get_upcoming_tasks(
    days: int = Query(default=7, ge=1, le=365, description="Number of days to look ahead"),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=1000),
    service: TaskService = Depends(get_task_service),
    current_user: User = Depends(get_current_user),
) -> list[TaskResponse]:
    """
    Get tasks due within the next `days` days for the authenticated user.

    Args:
        days: Look-ahead window in days (default 7)
        skip: Number of records to skip
        limit: Maximum number of records to return
        service: Task service dependency
        current_user: Authenticated user

    Returns:
        List of upcoming tasks ordered by due_date
    """
    tasks = service.get_upcoming_tasks(days=days, owner_id=current_user.id, skip=skip, limit=limit)
    return [service.to_response(task) for task in tasks]


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
    return service.to_response(task)


@router.patch("/{task_id}", response_model=TaskResponse)
async def update_task(
    task_id: int,
    task_data: TaskUpdate,
    service: TaskService = Depends(get_task_service),
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> TaskResponse:
    """
    Update an existing task (must belong to the authenticated user).

    Args:
        task_id: Task identifier
        task_data: Task update data
        service: Task service dependency
        session: Database session
        current_user: Authenticated user

    Returns:
        Updated task

    Raises:
        HTTPException: If task not found or not owned by current user
    """
    if task_data.category_id is not None:
        category = session.get(Category, task_data.category_id)
        if not category:
            raise HTTPException(status_code=404, detail="Category not found")

    task = service.update_task(task_id, task_data, owner_id=current_user.id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return service.to_response(task)


@router.post("/{task_id}/tags", response_model=TaskResponse)
def add_tag(
    task_id: int,
    tag_data: TagCreate,
    service: TaskService = Depends(get_task_service),
    current_user: User = Depends(get_current_user),
) -> TaskResponse:
    """
    Add a tag to an existing task (idempotent).

    Args:
        task_id: Task identifier
        tag_data: Tag to add
        service: Task service dependency
        current_user: Authenticated user

    Returns:
        Updated task

    Raises:
        HTTPException: 404 if task not found
    """
    task = service.add_tag(task_id, tag_data.name, owner_id=current_user.id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return service.to_response(task)


@router.delete("/{task_id}/tags/{tag_name}", response_model=TaskResponse)
def remove_tag(
    task_id: int,
    tag_name: str,
    service: TaskService = Depends(get_task_service),
    current_user: User = Depends(get_current_user),
) -> TaskResponse:
    """
    Remove a tag from a task.

    Args:
        task_id: Task identifier
        tag_name: Tag to remove
        service: Task service dependency
        current_user: Authenticated user

    Returns:
        Updated task

    Raises:
        HTTPException: 404 if task not found
    """
    task = service.remove_tag(task_id, tag_name, owner_id=current_user.id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return service.to_response(task)


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
    return service.to_response(updated_task)


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
