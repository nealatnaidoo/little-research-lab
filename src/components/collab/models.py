from dataclasses import dataclass
from uuid import UUID

from src.domain.entities import CollaborationGrant, CollabScope, User


@dataclass
class GrantAccessInput:
    actor: User
    content_id: UUID
    target_email: str
    scope: CollabScope


@dataclass
class RevokeAccessInput:
    actor: User
    content_id: UUID
    target_user_id: UUID


@dataclass
class ListCollaboratorsInput:
    actor: User
    content_id: UUID


@dataclass
class CollabOutput:
    grant: CollaborationGrant | None = None
    success: bool = False
    error: str | None = None


@dataclass
class CollabListOutput:
    collaborators: list[tuple[User, CollabScope]]
    success: bool = False
    error: str | None = None
