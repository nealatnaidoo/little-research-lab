from fastapi import APIRouter, Depends, HTTPException

from src.api.deps import get_auth_service, get_current_user
from src.api.schemas import UserCreateRequest, UserResponse, UserUpdateRequest
from src.domain.entities import User
from src.services.auth import AuthService

router = APIRouter()


@router.get("", response_model=list[UserResponse])
def list_users(
    current_user: User = Depends(get_current_user),
    service: AuthService = Depends(get_auth_service),
) -> list[UserResponse]:
    """List all users (admin only)."""
    try:
        users = service.list_users(current_user)
        return users  # type: ignore[return-value]
    except PermissionError:
        raise HTTPException(status_code=403, detail="Access denied") from None


@router.post("", response_model=UserResponse)
def create_user(
    req: UserCreateRequest,
    current_user: User = Depends(get_current_user),
    service: AuthService = Depends(get_auth_service),
) -> UserResponse:
    """Create a new user (admin only)."""
    try:
        user = service.create_user(
            actor=current_user,
            email=req.email,
            password=req.password,
            roles=req.roles,
            display_name=req.display_name,
        )
        return user  # type: ignore[return-value]
    except PermissionError:
        raise HTTPException(status_code=403, detail="Access denied") from None
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from None


@router.put("/{user_id}", response_model=UserResponse)
def update_user(
    user_id: str,
    req: UserUpdateRequest,
    current_user: User = Depends(get_current_user),
    service: AuthService = Depends(get_auth_service),
) -> UserResponse:
    """Update a user (admin only)."""
    try:
        user = service.update_user(
            actor=current_user,
            target_id=user_id,
            new_roles=req.roles,
            new_status=req.status,
        )
        return user  # type: ignore[return-value]
    except PermissionError:
        raise HTTPException(status_code=403, detail="Access denied") from None
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from None
