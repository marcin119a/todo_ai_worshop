"""Authentication endpoints: register and login."""

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlmodel import Session

from app.core.security import create_access_token, hash_password, verify_password
from app.db.models import User
from app.db.repository import UserRepository
from app.db.session import get_session
from app.schemas.auth import Token, UserCreate, UserResponse

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=UserResponse, status_code=201)
def register(user_data: UserCreate, session: Session = Depends(get_session)) -> UserResponse:
    """
    Register a new user account.

    Args:
        user_data: Email and password for the new account.

    Returns:
        Created user (without password).

    Raises:
        HTTPException: 400 if email is already taken.
    """
    repo = UserRepository(session)
    if repo.get_by_email(user_data.email):
        raise HTTPException(status_code=400, detail="Email already registered")
    user = repo.create(User(email=user_data.email, hashed_password=hash_password(user_data.password)))
    return UserResponse.model_validate(user)


@router.post("/login", response_model=Token)
def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    session: Session = Depends(get_session),
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
    repo = UserRepository(session)
    user = repo.get_by_email(form_data.username)
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    token = create_access_token({"sub": str(user.id), "is_admin": user.is_admin})
    return Token(access_token=token)
