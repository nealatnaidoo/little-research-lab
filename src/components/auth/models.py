from dataclasses import dataclass

from src.domain.entities import Session, User


@dataclass
class LoginInput:
    email: str
    password: str


@dataclass
class CreateSessionInput:
    user: User


@dataclass
class VerifySessionInput:
    token: str


@dataclass
class CreateUserInput:
    actor: User
    email: str
    password: str
    roles: list[str]
    display_name: str | None = None


@dataclass
class UpdateUserInput:
    actor: User
    target_id: str
    new_roles: list[str] | None = None
    new_status: str | None = None


@dataclass
class ListUsersInput:
    actor: User


@dataclass
class AuthOutput:
    user: User | None = None
    session: Session | None = None
    token_raw: str | None = None
    success: bool = False
    error: str | None = None


@dataclass
class UserOutput:
    user: User | None = None
    success: bool = False
    error: str | None = None


@dataclass
class UserListOutput:
    users: list[User]
    success: bool = False
    error: str | None = None
