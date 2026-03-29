"""Business logic layer for user operations."""

from typing import Optional

from app.core.security import create_access_token, hash_password, verify_password
from app.db.models import User
from app.db.repository import UserRepository
from app.schemas.auth import Token, UserCreate


class UserService:
    """Service layer for user registration and authentication."""

    def __init__(self, repository: UserRepository) -> None:
        self.repository = repository

    def register(self, user_data: UserCreate) -> Optional[User]:
        """Create a new user. Returns None if the email is already taken."""
        if self.repository.get_by_email(user_data.email):
            return None
        return self.repository.create(
            User(email=user_data.email, hashed_password=hash_password(user_data.password))
        )

    def authenticate(self, email: str, password: str) -> Optional[Token]:
        """Verify credentials and return a JWT token, or None if invalid."""
        user = self.repository.get_by_email(email)
        if not user or not verify_password(password, user.hashed_password):
            return None
        return Token(access_token=create_access_token({"sub": str(user.id)}))
