"""Pydantic schemas for authentication."""

from pydantic import BaseModel


class UserCreate(BaseModel):
    """Schema for user registration."""

    email: str
    password: str


class Token(BaseModel):
    """JWT token response."""

    access_token: str
    token_type: str = "bearer"


class UserResponse(BaseModel):
    """Public user data returned by the API."""

    id: int
    email: str
    is_admin: bool

    model_config = {"from_attributes": True}
