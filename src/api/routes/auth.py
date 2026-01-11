from datetime import timedelta
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Response, status
from fastapi.responses import RedirectResponse
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel

from src.adapters.sqlite.repos import SQLiteUserRepo
from src.api.auth_utils import (
    ACCESS_TOKEN_EXPIRE_MINUTES,
    create_access_token,
    verify_password,
)
from src.api.deps import get_current_user, get_user_repo
from src.domain.entities import User

router = APIRouter()


class Token(BaseModel):
    access_token: str
    token_type: str


class LoginRequest(BaseModel):
    username: str  # email
    password: str


@router.post("/login", response_model=Token)
async def login_for_access_token(
    response: Response,
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    user_repo: SQLiteUserRepo = Depends(get_user_repo),
) -> Token:
    """Authenticate user and return access token."""
    email = form_data.username
    password = form_data.password

    user = user_repo.get_by_email(email)
    if not user or not verify_password(password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if user.status != "active":
        raise HTTPException(status_code=400, detail="User account is inactive")

    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": str(user.id)}, expires_delta=access_token_expires
    )

    # Set HttpOnly Cookie
    response.set_cookie(
        key="access_token",
        value=f"Bearer {access_token}",
        httponly=True,
        max_age=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        expires=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        samesite="lax",
        secure=False,  # Set to True for HTTPS prod
    )

    return Token(access_token=access_token, token_type="bearer")


@router.post("/logout")
def logout(response: Response) -> dict[str, str]:
    """Log out user by clearing cookie."""
    response.delete_cookie(key="access_token")
    return {"status": "success"}


@router.get("/me")
def read_users_me(
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    """Get current user info."""
    return {
        "id": str(current_user.id),
        "email": current_user.email,
        "display_name": current_user.display_name,
        "roles": current_user.roles,
    }


@router.get("/dev/login")
def dev_force_login(
    user_repo: SQLiteUserRepo = Depends(get_user_repo),
) -> RedirectResponse:
    """Dev-only: Auto-login as admin for testing."""
    user = user_repo.get_by_email("admin@example.com")
    if not user:
        raise HTTPException(404, "Admin not found (Seed DB first)")

    access_token_expires = timedelta(minutes=60 * 24)
    access_token = create_access_token(
        data={"sub": str(user.id)}, expires_delta=access_token_expires
    )

    resp = RedirectResponse(url="http://localhost:3000/admin")
    resp.set_cookie(
        key="access_token",
        value=f"Bearer {access_token}",
        httponly=True,
        max_age=60 * 60 * 24,
        expires=60 * 60 * 24,
        samesite="lax",
        secure=False,
    )
    return resp
