from dataclasses import dataclass

from src.domain.entities import RoleType, User


@dataclass
class CreateInviteInput:
    creator: User
    role: RoleType
    days_valid: int = 7


@dataclass
class RedeemInviteInput:
    token: str
    email: str
    display_name: str
    password: str


@dataclass
class InviteOutput:
    token: str | None = None
    success: bool = False
    error: str | None = None


@dataclass
class RedeemOutput:
    user: User | None = None
    success: bool = False
    error: str | None = None
