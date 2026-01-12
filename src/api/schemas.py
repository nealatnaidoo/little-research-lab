from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel

# --- Shared Enums/Types ---
BlockType = Literal["markdown", "image", "chart", "embed", "divider"]
ContentStatus = Literal["draft", "scheduled", "published", "archived"]
Visibility = Literal["public", "unlisted", "private"]
ContentType = Literal["post", "page"]


# --- Content Blocks ---
class ContentBlockModel(BaseModel):
    id: str | None = None
    block_type: BlockType
    data_json: dict[str, Any]
    position: int | None = None  # Position is implicit in list order for domain


# --- Content Items ---
class ContentItemBase(BaseModel):
    title: str
    slug: str
    summary: str | None = None
    status: ContentStatus = "draft"
    visibility: Visibility = "public"
    publish_at: datetime | None = None


class ContentCreateRequest(ContentItemBase):
    type: ContentType
    blocks: list[ContentBlockModel] = []


class ContentUpdateRequest(BaseModel):
    title: str | None = None
    slug: str | None = None
    summary: str | None = None
    status: ContentStatus | None = None
    visibility: Visibility | None = None
    publish_at: datetime | None = None
    blocks: list[ContentBlockModel] | None = None


class ContentTransitionRequest(BaseModel):
    status: ContentStatus
    publish_at: datetime | None = None


class ContentItemResponse(ContentItemBase):
    id: UUID
    type: ContentType
    published_at: datetime | None = None
    owner_user_id: UUID
    created_at: datetime
    updated_at: datetime
    blocks: list[ContentBlockModel] = []

    class Config:
        from_attributes = True


# --- Assets ---
class AssetResponse(BaseModel):
    id: UUID
    filename_original: str
    mime_type: str
    size_bytes: int
    visibility: Visibility
    created_at: datetime

    class Config:
        from_attributes = True


# --- Users ---
class UserResponse(BaseModel):
    id: UUID
    email: str
    display_name: str | None = None
    roles: list[str] = []
    status: str
    created_at: datetime

    class Config:
        from_attributes = True


class UserCreateRequest(BaseModel):
    email: str
    display_name: str | None = None
    password: str
    roles: list[str] = ["editor"]


class UserUpdateRequest(BaseModel):
    roles: list[str] | None = None
    status: str | None = None  # "active", "disabled"
