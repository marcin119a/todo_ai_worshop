"""Pydantic schemas for task API requests and responses."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field

from app.db.models import Priority, Status


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

    pass


class TaskUpdate(BaseModel):
    """Schema for updating an existing task."""

    title: Optional[str] = Field(default=None, max_length=200)
    description: Optional[str] = Field(default=None, max_length=1000)
    priority: Optional[Priority] = None
    priority_reason: Optional[str] = Field(default=None, max_length=500)
    status: Optional[Status] = None


class TaskResponse(TaskBase):
    """Schema for task API responses."""

    id: int
    priority_reason: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


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

