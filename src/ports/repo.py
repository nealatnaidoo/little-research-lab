from typing import Any, Protocol
from uuid import UUID

from src.domain.entities import Asset, CollaborationGrant, ContentItem, Invite, LinkItem, SiteSettings, User


class UserRepoPort(Protocol):
    def get_by_email(self, email: str) -> User | None:
        ...
        
    def get_by_id(self, user_id: UUID) -> User | None:
        ...
        
    def list_all(self) -> list[User]:
        ...
    
    def save(self, user: User) -> None:
        ...


class ContentRepoPort(Protocol):
    def save(self, content: ContentItem) -> ContentItem:
        ...

    def get_by_id(self, item_id: UUID) -> ContentItem | None:
        ...
        
    def get_by_slug(self, slug: str, item_type: str) -> ContentItem | None:
        ...

    def list_items(self, filters: dict[str, Any]) -> list[ContentItem]:
        ...
        
    def delete(self, item_id: UUID) -> None:
        ...

class LinkRepoPort(Protocol):
    def save(self, link: LinkItem) -> LinkItem:
        ...
    
    def get_all(self) -> list[LinkItem]:
        ...
    
    def delete(self, link_id: UUID) -> None:
        ...

class AssetRepoPort(Protocol):
    def save(self, asset: Asset) -> Asset:
        ...
        
    def get_by_id(self, asset_id: UUID) -> Asset | None:
        ...
        
    def list_assets(self) -> list[Asset]:
        ...

class InviteRepoPort(Protocol):
    def save(self, invite: Invite) -> None:
        ...
        
    def get_by_token_hash(self, token_hash: str) -> Invite | None:
        ...
        
    def get_pending(self) -> list[Invite]:
        """List active, unredeemed invites."""
        ...

class CollabRepoPort(Protocol):
    def save(self, grant: "CollaborationGrant") -> None:
        ...

    def delete(self, grant_id: UUID) -> None:
        ...

    def get_by_content_and_user(
        self, content_id: UUID, user_id: UUID
    ) -> "CollaborationGrant | None":
        ...

    def list_by_content(self, content_id: UUID) -> list["CollaborationGrant"]:
        ...


class SiteSettingsRepoPort(Protocol):
    """Repository for site-wide settings (single row)."""

    def get(self) -> SiteSettings | None:
        """Get current site settings, or None if not configured."""
        ...

    def save(self, settings: SiteSettings) -> SiteSettings:
        """Save or update site settings."""
        ...
