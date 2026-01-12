"""
v3 Domain Entities for little-research-lab.

These entities extend the domain model with v3-specific requirements:
- E3/E4: Asset + AssetVersion (immutable versioning)
- E5: PublishJob (idempotent scheduling)
- E6: AnalyticsEventAggregate (privacy-minimal analytics)
- E7: RedirectRule (redirect management)

Existing entities (User, ContentItem, SiteSettings, AuditEvent) are
imported from src.domain.entities for backward compatibility.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Literal
from uuid import UUID, uuid4

from pydantic import BaseModel, Field

# Re-export existing entities for convenience
from src.domain.entities import (
    Asset,
    AuditEvent,
    ContentBlock,
    ContentItem,
    ContentStatus,
    ContentType,
    ContentVisibility,
    SiteSettings,
    User,
)

__all__ = [
    # Existing entities
    "Asset",
    "AuditEvent",
    "ContentBlock",
    "ContentItem",
    "ContentStatus",
    "ContentType",
    "ContentVisibility",
    "SiteSettings",
    "User",
    # New v3 entities
    "AssetVersion",
    "PublishJob",
    "PublishJobStatus",
    "AnalyticsEventAggregate",
    "RedirectRule",
]


# --- E4: AssetVersion (Immutable) ---


class AssetVersion(BaseModel):
    """
    Immutable asset version (E4).

    Invariants:
    - I3: bytes are immutable; sha256 stored equals sha256 served
    - I4: /latest alias resolves to exactly one version at a time
    """

    id: UUID = Field(default_factory=uuid4)
    asset_id: UUID  # Foreign key to Asset
    version_number: int  # Monotonically increasing
    storage_key: str  # Immutable key in object storage
    sha256: str  # Content hash for integrity verification
    size_bytes: int
    mime_type: str
    filename_original: str
    is_latest: bool = False  # Only one version per asset can be latest
    created_by_user_id: UUID
    created_at: datetime = Field(default_factory=datetime.utcnow)


# --- E5: PublishJob (Scheduler) ---

PublishJobStatus = Literal["queued", "running", "succeeded", "retry_wait", "failed"]


@dataclass(frozen=False)
class PublishJob:
    """
    Publish job for scheduled content (E5).

    Invariants:
    - I5: at-most-once per idempotency key (content_id, publish_at_utc)

    State machine (SM2):
    - queued -> running -> succeeded
    - queued|running -> retry_wait -> running
    - running -> failed (after max attempts)
    """

    content_id: UUID
    publish_at_utc: datetime
    # Fields with defaults must follow non-default fields
    id: UUID = field(default_factory=uuid4)
    status: PublishJobStatus = "queued"
    attempts: int = 0
    last_attempt_at: datetime | None = None
    next_retry_at: datetime | None = None
    completed_at: datetime | None = None
    actual_publish_at: datetime | None = None
    error_message: str | None = None
    claimed_by: str | None = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)


# --- E6: AnalyticsEventAggregate ---


class AnalyticsEventAggregate(BaseModel):
    """
    Aggregated analytics data (E6).

    Invariants:
    - I6: no PII fields (no IP, no full UA, no cookies, no visitor IDs)

    Buckets: minute, hour, day (per rules.analytics.aggregation.buckets)
    """

    id: UUID = Field(default_factory=uuid4)
    bucket_type: Literal["minute", "hour", "day"]
    bucket_start: datetime  # Start of the time bucket (UTC)
    event_type: Literal["page_view", "outbound_click", "asset_download"]
    content_id: UUID | None = None  # Optional content reference
    asset_id: UUID | None = None  # Optional asset reference
    link_id: UUID | None = None  # Optional outbound link reference

    # Attribution dimensions (no PII)
    utm_source: str | None = None
    utm_medium: str | None = None
    utm_campaign: str | None = None
    referrer_domain: str | None = None
    ua_class: Literal["bot", "real", "unknown"] = "unknown"

    # Aggregate counts
    count_total: int = 0
    count_real: int = 0  # Excludes bots
    count_bot: int = 0

    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


# --- E7: RedirectRule ---


class RedirectRule(BaseModel):
    """
    Redirect rule for URL management (E7).

    Invariants:
    - I7: no loops, no open redirects (targets must be internal)

    Constraints (per rules.redirects):
    - max_chain_length: 3
    - prevent_loops: true
    - prevent_collisions_with_routes: true
    """

    id: UUID = Field(default_factory=uuid4)
    source_path: str  # e.g., "/old-path"
    target_path: str  # e.g., "/new-path" (must be internal)
    status_code: int = 301  # 301 or 302
    is_active: bool = True
    preserve_query_params: bool = True
    created_by_user_id: UUID
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
