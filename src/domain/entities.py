from datetime import datetime
from typing import Any, Literal
from uuid import UUID, uuid4

from pydantic import BaseModel, Field

# --- Enums / Literals ---
RoleType = Literal["owner", "admin", "publisher", "editor", "viewer"]
ContentType = Literal["post", "page"]
ContentStatus = Literal["draft", "scheduled", "published", "archived"]
ContentVisibility = Literal["public", "unlisted", "private"]
BlockType = Literal["markdown", "image", "chart", "embed", "divider"]
LinkStatus = Literal["active", "disabled"]
CollabScope = Literal["view", "edit"]

# --- User & Auth ---

class User(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    email: str
    display_name: str
    password_hash: str
    roles: list[RoleType] = Field(default_factory=list)
    status: Literal["active", "disabled"] = "active"
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

class RoleAssignment(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    user_id: UUID
    role: RoleType
    created_at: datetime = Field(default_factory=datetime.utcnow)

class Session(BaseModel):
    id: str  # Token or Session ID
    user_id: UUID
    token_hash: str
    expires_at: datetime
    created_at: datetime = Field(default_factory=datetime.utcnow)

# --- Assets ---

class Asset(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    filename_original: str
    mime_type: str
    size_bytes: int
    sha256: str
    storage_path: str
    visibility: ContentVisibility = "private"
    created_by_user_id: UUID
    created_at: datetime = Field(default_factory=datetime.utcnow)

# --- Content ---

class ContentBlock(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    block_type: BlockType
    data_json: dict[str, Any]
    # Position is implicitly defined by list order in ContentItem

class ContentRevision(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    content_item_id: UUID
    revision_no: int
    snapshot_json: str  # Serialized ContentItem state
    created_by_user_id: UUID
    created_at: datetime = Field(default_factory=datetime.utcnow)

class ContentItem(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    type: ContentType
    slug: str
    title: str
    summary: str = ""
    status: ContentStatus = "draft"
    
    publish_at: datetime | None = None
    published_at: datetime | None = None
    
    owner_user_id: UUID
    visibility: ContentVisibility = "public"
    
    blocks: list[ContentBlock] = Field(default_factory=list)
    
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

# --- Links ---

class LinkItem(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    slug: str
    title: str
    url: str
    icon: str | None = None
    status: LinkStatus = "active"
    position: int = 0
    visibility: ContentVisibility = "public"
    group_id: UUID | None = None

class LinkGroup(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    title: str
    position: int = 0
    visibility: ContentVisibility = "public"

# --- Collaboration ---

class Invite(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    token_hash: str
    role: RoleType = "viewer"
    expires_at: datetime
    redeemed_at: datetime | None = None
    redeemed_by_user_id: UUID | None = None
    created_at: datetime = Field(default_factory=datetime.utcnow)

class CollaborationGrant(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    content_item_id: UUID
    user_id: UUID
    scope: CollabScope
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
# --- Config/Audit ---

class SiteSettings(BaseModel):
    site_title: str
    site_subtitle: str
    avatar_asset_id: UUID | None = None
    theme: Literal["light", "dark", "system"] = "system"
    social_links_json: dict[str, str] = Field(default_factory=dict)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

class AuditEvent(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    actor_user_id: UUID | None
    action: str
    target_type: str
    target_id: str
    meta_json: dict[str, Any]
    created_at: datetime = Field(default_factory=datetime.utcnow)
