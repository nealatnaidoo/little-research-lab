from typing import Any

from fastapi import APIRouter, Depends, HTTPException

from src.api.deps import (
    get_auth_adapter,
    get_clock,
    get_current_user,
    get_policy,
    get_session_store,
    get_user_repo,
)
from src.api.schemas import UserCreateRequest, UserResponse, UserUpdateRequest
from src.components.auth.component import run_create_user, run_list_users, run_update_user
from src.components.auth.models import CreateUserInput, ListUsersInput, UpdateUserInput
from src.domain.entities import User

router = APIRouter()


@router.get("", response_model=list[UserResponse])
def list_users(
    current_user: User = Depends(get_current_user),
    user_repo: Any = Depends(get_user_repo),
    policy: Any = Depends(get_policy),
) -> list[UserResponse]:
    """List all users (admin only)."""
    inp = ListUsersInput(actor=current_user)
    result = run_list_users(inp, user_repo=user_repo, policy=policy)

    if not result.success:
        raise HTTPException(status_code=403, detail=result.error or "Access denied")

    return result.users  # type: ignore


@router.post("", response_model=UserResponse)
def create_user(
    req: UserCreateRequest,
    current_user: User = Depends(get_current_user),
    user_repo: Any = Depends(get_user_repo),
    policy: Any = Depends(get_policy),
    auth_adapter: Any = Depends(get_auth_adapter),
    clock: Any = Depends(get_clock),
) -> UserResponse:
    """Create a new user (admin only)."""
    inp = CreateUserInput(
        actor=current_user,
        email=req.email,
        password=req.password,
        roles=req.roles,
        display_name=req.display_name,
    )
    result = run_create_user(
        inp,
        user_repo=user_repo,
        auth_adapter=auth_adapter,
        policy=policy,
        time=clock,
    )

    if not result.success:
        if result.error == "Access denied":
            raise HTTPException(status_code=403, detail="Access denied")
        raise HTTPException(status_code=400, detail=result.error)

    return result.user  # type: ignore


@router.put("/{user_id}", response_model=UserResponse)
def update_user(
    user_id: str,
    req: UserUpdateRequest,
    current_user: User = Depends(get_current_user),
    user_repo: Any = Depends(get_user_repo),
    policy: Any = Depends(get_policy),
    session_store: Any = Depends(get_session_store),
    clock: Any = Depends(get_clock),
) -> UserResponse:
    """Update a user (admin only)."""
    inp = UpdateUserInput(
        actor=current_user,
        target_id=user_id,
        new_roles=req.roles,
        new_status=req.status,
    )
    result = run_update_user(
        inp,
        user_repo=user_repo,
        policy=policy,
        session_store=session_store,
        time=clock,
    )

    if not result.success:
        if result.error == "Access denied":
            raise HTTPException(status_code=403, detail="Access denied")
        if result.error == "User not found":
            raise HTTPException(status_code=404, detail="User not found")
        raise HTTPException(status_code=400, detail=result.error)

    return result.user  # type: ignore
