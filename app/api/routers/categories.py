"""API routes for category operations."""

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session

from app.api.deps import get_current_user
from app.db.models import User
from app.db.repository import CategoryRepository
from app.db.session import get_session
from app.schemas.task import CategoryCreate, CategoryResponse
from app.services.category_service import CategoryService

router = APIRouter(prefix="/categories", tags=["categories"])


def get_category_repository(session: Session = Depends(get_session)) -> CategoryRepository:
    return CategoryRepository(session)


def get_category_service(
    repository: CategoryRepository = Depends(get_category_repository),
) -> CategoryService:
    return CategoryService(repository)


@router.post("/", response_model=CategoryResponse, status_code=201)
def create_category(
    data: CategoryCreate,
    service: CategoryService = Depends(get_category_service),
    _: User = Depends(get_current_user),
) -> CategoryResponse:
    """Create a new category.

    Args:
        data: Category creation data
        service: Category service dependency

    Returns:
        Created category

    Raises:
        HTTPException: 409 if a category with that name already exists
    """
    category, created = service.create_category(data)
    if not created:
        raise HTTPException(status_code=409, detail="Category with this name already exists")
    return CategoryResponse.model_validate(category)


@router.delete("/{category_id}", status_code=200)
def delete_category(
    category_id: int,
    service: CategoryService = Depends(get_category_service),
    _: User = Depends(get_current_user),
) -> dict:
    """Delete a category and nullify category_id on all assigned tasks.

    Args:
        category_id: Category identifier
        service: Category service dependency

    Returns:
        Confirmation message

    Raises:
        HTTPException: 404 if category not found
    """
    category = service.delete_category(category_id)
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")
    return {"detail": "Category deleted"}
