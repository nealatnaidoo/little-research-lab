"""
Monetization component models (C11).

Data models for content monetization and paywall enforcement.

Spec refs: E17.1, E17.2, E17.3
Invariants: I10 (server-side enforcement), R8 (no client-side bypass)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

from src.domain.entities import ContentTier

# --- Entitlements ---

EntitlementLevel = Literal["free", "premium", "subscriber"]


@dataclass(frozen=True)
class VisitorEntitlement:
    """
    Visitor's content entitlement level.

    Determines which content tiers the visitor can access.
    """

    level: EntitlementLevel = "free"
    visitor_id: str | None = None  # Optional, for logged-in users


# --- Access Control ---


@dataclass(frozen=True)
class AccessCheckInput:
    """Input for checking content access."""

    content_tier: ContentTier
    entitlement: VisitorEntitlement


@dataclass(frozen=True)
class AccessCheckOutput:
    """Output from access check."""

    has_full_access: bool
    preview_blocks: int | None = None  # None means full access
    reason: str | None = None


# --- Preview Calculation ---


@dataclass(frozen=True)
class PreviewBlocksInput:
    """Input for calculating preview blocks."""

    content_tier: ContentTier
    total_blocks: int


@dataclass(frozen=True)
class PreviewBlocksOutput:
    """Output with preview block calculation."""

    preview_count: int | None  # None means no limit (full access)
    is_limited: bool
    blocks_hidden: int


# --- Content Filtering ---


@dataclass(frozen=True)
class FilterContentInput:
    """Input for filtering content blocks based on access."""

    blocks: list[dict[str, Any]]
    content_tier: ContentTier
    entitlement: VisitorEntitlement


@dataclass(frozen=True)
class FilterContentOutput:
    """Output with filtered content blocks."""

    blocks: list[dict[str, Any]]
    is_preview: bool
    total_blocks: int
    visible_blocks: int
    hidden_blocks: int


# --- Configuration ---


@dataclass(frozen=True)
class MonetizationConfig:
    """Monetization configuration from rules."""

    enabled: bool = False
    preview_blocks: dict[str, int | None] = field(
        default_factory=lambda: {
            "free": None,  # No limit
            "premium": 3,
            "subscriber_only": 2,
        }
    )
    default_tier: ContentTier = "free"


# --- Entitlement Mapping ---

# Maps entitlement levels to accessible content tiers
ENTITLEMENT_ACCESS: dict[EntitlementLevel, set[ContentTier]] = {
    "free": {"free"},
    "premium": {"free", "premium"},
    "subscriber": {"free", "premium", "subscriber_only"},
}


def can_access_tier(entitlement: EntitlementLevel, content_tier: ContentTier) -> bool:
    """Check if entitlement level can access content tier."""
    return content_tier in ENTITLEMENT_ACCESS.get(entitlement, {"free"})
