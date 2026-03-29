"""Pydantic schemas for task API requests and responses."""

from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, Field, field_validator

from app.db.models import Priority, Status


class CategoryCreate(BaseModel):
    """Schema for creating a new category."""

    name: str = Field(max_length=100, description="Category name")
    color: Optional[str] = Field(default=None, max_length=20, description="Hex color code")


class CategoryResponse(BaseModel):
    """Schema for category API responses."""

    id: int
    name: str
    color: Optional[str] = None

    model_config = {"from_attributes": True}


class TagCreate(BaseModel):
    """Schema for adding a tag to a task."""

    name: str = Field(max_length=100, description="Tag name")


class TaskBase(BaseModel):
    """Base task schema with common fields."""

    title: str = Field(max_length=200, description="Task title")
    description: Optional[str] = Field(
        default=None,
        max_length=1000,
        description="Task description",
    )
    priority: Priority = Field(default=Priority.MEDIUM, description="Task priority level")
    status: Status = Field(default=Status.TODO, description="Task status")


class TaskCreate(TaskBase):
    """Schema for creating a new task."""

    category_id: Optional[int] = None
    tags: list[str] = []
    due_date: Optional[date] = None


class TaskUpdate(BaseModel):
    """Schema for updating an existing task."""

    title: Optional[str] = Field(default=None, max_length=200)
    description: Optional[str] = Field(default=None, max_length=1000)
    priority: Optional[Priority] = None
    priority_reason: Optional[str] = Field(default=None, max_length=500)
    status: Optional[Status] = None
    category_id: Optional[int] = None
    due_date: Optional[date] = None


class TaskResponse(TaskBase):
    """Schema for task API responses."""

    id: int
    priority_reason: Optional[str] = None
    due_date: Optional[date] = None
    created_at: datetime
    updated_at: datetime
    category: Optional[CategoryResponse] = None
    tags: list[str] = []
    ai_override: bool = False

    model_config = {"from_attributes": True}

    @field_validator("tags", mode="before")
    @classmethod
    def normalize_tags(cls, v: object) -> list[str]:
        return v if v is not None else []


class PriorityAnalysisRequest(BaseModel):
    """Request schema for standalone priority analysis endpoint."""

    title: str = Field(max_length=200, description="Task title")
    description: Optional[str] = Field(
        default=None,
        max_length=1000,
        description="Task description",
    )


class PriorityAnalysisResponse(BaseModel):
    """Response schema for standalone priority analysis endpoint."""

    priority: Priority = Field(description="Suggested task priority level")
    priority_reason: str = Field(description="Reason for the suggested priority")
