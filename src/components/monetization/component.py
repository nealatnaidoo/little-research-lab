"""
Monetization component (C11).

Pure functions for content monetization and paywall enforcement.

Spec refs: E17.2, E17.3
Invariants: I10 (server-side enforcement), R8 (no client-side bypass)
Test assertions: TA-0093-0096
"""

from __future__ import annotations

from typing import Any

from src.domain.entities import ContentTier

from .models import (
    AccessCheckInput,
    AccessCheckOutput,
    FilterContentInput,
    FilterContentOutput,
    MonetizationConfig,
    PreviewBlocksInput,
    PreviewBlocksOutput,
    VisitorEntitlement,
    can_access_tier,
)
from .ports import PaymentPort

# --- Pure Functions ---


def check_access(
    content_tier: ContentTier,
    entitlement: VisitorEntitlement,
    config: MonetizationConfig | None = None,
) -> AccessCheckOutput:
    """
    Check if visitor has full access to content (TA-0093).

    Pure function that determines access based on entitlement vs tier.

    Args:
        content_tier: The content's tier (free/premium/subscriber_only)
        entitlement: Visitor's entitlement level
        config: Optional monetization config

    Returns:
        AccessCheckOutput with access determination
    """
    config = config or MonetizationConfig()

    # If monetization disabled, everyone has full access
    if not config.enabled:
        return AccessCheckOutput(
            has_full_access=True,
            preview_blocks=None,
            reason="Monetization disabled",
        )

    # Check if entitlement grants access to this tier
    has_access = can_access_tier(entitlement.level, content_tier)

    if has_access:
        return AccessCheckOutput(
            has_full_access=True,
            preview_blocks=None,
            reason=f"Entitlement '{entitlement.level}' grants access to '{content_tier}'",
        )

    # No full access - determine preview blocks
    preview_count = config.preview_blocks.get(content_tier)

    return AccessCheckOutput(
        has_full_access=False,
        preview_blocks=preview_count,
        reason=f"Entitlement '{entitlement.level}' cannot access '{content_tier}'",
    )


def calculate_preview_blocks(
    content_tier: ContentTier,
    total_blocks: int,
    config: MonetizationConfig | None = None,
) -> PreviewBlocksOutput:
    """
    Calculate number of preview blocks for a content tier (TA-0095).

    Pure function using rules-driven configuration.

    Args:
        content_tier: The content's tier
        total_blocks: Total number of blocks in content
        config: Monetization configuration

    Returns:
        PreviewBlocksOutput with preview calculation
    """
    config = config or MonetizationConfig()

    # Get preview limit for this tier
    preview_limit = config.preview_blocks.get(content_tier)

    # None means no limit (full access for free tier)
    if preview_limit is None:
        return PreviewBlocksOutput(
            preview_count=None,
            is_limited=False,
            blocks_hidden=0,
        )

    # Calculate actual preview count (can't exceed total)
    actual_preview = min(preview_limit, total_blocks)
    hidden = max(0, total_blocks - actual_preview)

    return PreviewBlocksOutput(
        preview_count=actual_preview,
        is_limited=hidden > 0,
        blocks_hidden=hidden,
    )


def filter_content_blocks(
    blocks: list[dict[str, Any]],
    content_tier: ContentTier,
    entitlement: VisitorEntitlement,
    config: MonetizationConfig | None = None,
) -> FilterContentOutput:
    """
    Filter content blocks based on access level (TA-0096, I10, R8).

    Server-side enforcement - returns only accessible blocks.
    This is the key function that ensures R8 (no client-side bypass).

    Args:
        blocks: All content blocks
        content_tier: The content's tier
        entitlement: Visitor's entitlement
        config: Monetization configuration

    Returns:
        FilterContentOutput with filtered blocks
    """
    config = config or MonetizationConfig()
    total_blocks = len(blocks)

    # Check access
    access = check_access(content_tier, entitlement, config)

    if access.has_full_access:
        return FilterContentOutput(
            blocks=blocks,
            is_preview=False,
            total_blocks=total_blocks,
            visible_blocks=total_blocks,
            hidden_blocks=0,
        )

    # Calculate preview
    preview = calculate_preview_blocks(content_tier, total_blocks, config)

    if preview.preview_count is None:
        # No limit
        return FilterContentOutput(
            blocks=blocks,
            is_preview=False,
            total_blocks=total_blocks,
            visible_blocks=total_blocks,
            hidden_blocks=0,
        )

    # Return only preview blocks (server-side enforcement)
    visible_blocks = blocks[: preview.preview_count]

    return FilterContentOutput(
        blocks=visible_blocks,
        is_preview=True,
        total_blocks=total_blocks,
        visible_blocks=len(visible_blocks),
        hidden_blocks=preview.blocks_hidden,
    )


def get_paywall_info(
    content_tier: ContentTier,
    total_blocks: int,
    entitlement: VisitorEntitlement,
    config: MonetizationConfig | None = None,
) -> dict[str, Any]:
    """
    Get paywall display information for frontend (TA-0094).

    Returns metadata for rendering paywall overlay.
    Does NOT include hidden content (enforces R8).

    Args:
        content_tier: The content's tier
        total_blocks: Total blocks in content
        entitlement: Visitor's entitlement
        config: Monetization configuration

    Returns:
        Dict with paywall display info
    """
    config = config or MonetizationConfig()

    access = check_access(content_tier, entitlement, config)
    preview = calculate_preview_blocks(content_tier, total_blocks, config)

    return {
        "show_paywall": not access.has_full_access and preview.is_limited,
        "content_tier": content_tier,
        "entitlement_level": entitlement.level,
        "preview_blocks": preview.preview_count,
        "total_blocks": total_blocks,
        "hidden_blocks": preview.blocks_hidden,
        "cta_text": "Subscribe to read more",
        "monetization_enabled": config.enabled,
    }


# --- Run Function (Atomic Component Pattern) ---


def run(
    input_data: AccessCheckInput | PreviewBlocksInput | FilterContentInput,
    config: MonetizationConfig | None = None,
    payment_adapter: PaymentPort | None = None,
) -> AccessCheckOutput | PreviewBlocksOutput | FilterContentOutput:
    """
    Run monetization operation based on input type.

    This is the main entry point following the atomic component pattern.

    Args:
        input_data: One of the input types
        config: Monetization configuration
        payment_adapter: Optional payment port for entitlement checks

    Returns:
        Corresponding output type
    """
    config = config or MonetizationConfig()

    if isinstance(input_data, AccessCheckInput):
        return check_access(
            input_data.content_tier,
            input_data.entitlement,
            config,
        )

    if isinstance(input_data, PreviewBlocksInput):
        return calculate_preview_blocks(
            input_data.content_tier,
            input_data.total_blocks,
            config,
        )

    if isinstance(input_data, FilterContentInput):
        return filter_content_blocks(
            input_data.blocks,
            input_data.content_tier,
            input_data.entitlement,
            config,
        )

    raise TypeError(f"Unknown input type: {type(input_data)}")


# --- Configuration Loader ---


def load_config_from_rules(rules: dict[str, Any]) -> MonetizationConfig:
    """
    Load MonetizationConfig from rules.yaml.

    Args:
        rules: Parsed rules dictionary

    Returns:
        MonetizationConfig instance
    """
    monetization = rules.get("monetization", {})
    content_tiers = rules.get("content", {}).get("tiers", {})

    # Prefer content.tiers.preview_blocks, fall back to monetization.paywall.preview_blocks
    preview_blocks = content_tiers.get("preview_blocks") or monetization.get(
        "paywall", {}
    ).get("preview_blocks", {})

    return MonetizationConfig(
        enabled=monetization.get("enabled", False),
        preview_blocks=preview_blocks
        or {"free": None, "premium": 3, "subscriber_only": 2},
        default_tier=content_tiers.get("default", "free"),
    )
