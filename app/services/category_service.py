"""Business logic layer for category operations."""

from typing import Optional

from app.db.models import Category
from app.db.repository import CategoryRepository
from app.schemas.task import CategoryCreate


class CategoryService:
    """Service layer for category business logic."""

    def __init__(self, repository: CategoryRepository) -> None:
        self.repository = repository

    def create_category(self, data: CategoryCreate) -> tuple[Category, bool]:
        """
        Create a new category.

        Returns:
            Tuple of (category, created) where created=False means name already exists.
        """
        existing = self.repository.get_by_name(data.name)
        if existing:
            return existing, False
        category = Category(name=data.name, color=data.color)
        return self.repository.create(category), True

    def delete_category(self, category_id: int) -> Optional[Category]:
        """
        Delete a category and nullify all tasks assigned to it.

        Returns:
            The deleted Category if found, None otherwise.
        """
        category = self.repository.get_by_id(category_id)
        if not category:
            return None
        self.repository.delete_and_nullify_tasks(category_id)
        return category
