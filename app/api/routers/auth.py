"""Authentication endpoints: register and login."""

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlmodel import Session

from app.db.repository import UserRepository
from app.db.session import get_session
from app.schemas.auth import Token, UserCreate, UserResponse
from app.services.user_service import UserService

router = APIRouter(prefix="/auth", tags=["auth"])


def get_user_service(session: Session = Depends(get_session)) -> UserService:
    """Dependency to get user service."""
    return UserService(UserRepository(session))


@router.post("/register", response_model=UserResponse, status_code=201)
def register(
    user_data: UserCreate,
    service: UserService = Depends(get_user_service),
) -> UserResponse:
    """
    Register a new user account.

    Args:
        user_data: Email and password for the new account.

    Returns:
        Created user (without password).

    Raises:
        HTTPException: 400 if email is already taken.
    """
    user = service.register(user_data)
    if not user:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered")
    return UserResponse.model_validate(user)


@router.post("/login", response_model=Token)
def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    service: UserService = Depends(get_user_service),
) -> Token:
    """
    Authenticate and receive a JWT access token.

    Args:
        form_data: OAuth2 form with username (email) and password.

    Returns:
        Bearer JWT token.

    Raises:
        HTTPException: 401 if credentials are invalid.
    """
    token = service.authenticate(form_data.username, form_data.password)
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    return token
