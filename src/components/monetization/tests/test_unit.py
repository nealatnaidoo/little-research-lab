"""
Unit tests for monetization component (C11).

Tests:
- TA-0093: Access check based on entitlement vs tier
- TA-0094: Paywall info generation
- TA-0095: Preview block calculation
- TA-0096: Server-side content filtering (I10, R8)
"""

from typing import Any

import pytest

from src.components.monetization import (
    AccessCheckInput,
    AccessCheckOutput,
    FilterContentInput,
    FilterContentOutput,
    MonetizationConfig,
    PreviewBlocksInput,
    PreviewBlocksOutput,
    VisitorEntitlement,
    calculate_preview_blocks,
    can_access_tier,
    check_access,
    filter_content_blocks,
    get_paywall_info,
    load_config_from_rules,
    run,
)

# --- Fixtures ---


@pytest.fixture
def enabled_config() -> MonetizationConfig:
    """Config with monetization enabled."""
    return MonetizationConfig(
        enabled=True,
        preview_blocks={"free": None, "premium": 3, "subscriber_only": 2},
        default_tier="free",
    )


@pytest.fixture
def disabled_config() -> MonetizationConfig:
    """Config with monetization disabled."""
    return MonetizationConfig(enabled=False)


@pytest.fixture
def free_entitlement() -> VisitorEntitlement:
    """Free tier entitlement."""
    return VisitorEntitlement(level="free")


@pytest.fixture
def premium_entitlement() -> VisitorEntitlement:
    """Premium tier entitlement."""
    return VisitorEntitlement(level="premium")


@pytest.fixture
def subscriber_entitlement() -> VisitorEntitlement:
    """Subscriber tier entitlement."""
    return VisitorEntitlement(level="subscriber")


@pytest.fixture
def sample_blocks() -> list[dict[str, Any]]:
    """Sample content blocks."""
    return [
        {"id": "1", "type": "text", "content": "Block 1"},
        {"id": "2", "type": "text", "content": "Block 2"},
        {"id": "3", "type": "text", "content": "Block 3"},
        {"id": "4", "type": "text", "content": "Block 4"},
        {"id": "5", "type": "text", "content": "Block 5"},
    ]


# --- Entitlement Access Tests ---


class TestEntitlementAccess:
    """Tests for entitlement access mapping."""

    def test_free_can_access_free(self) -> None:
        """Free entitlement can access free content."""
        assert can_access_tier("free", "free") is True

    def test_free_cannot_access_premium(self) -> None:
        """Free entitlement cannot access premium content."""
        assert can_access_tier("free", "premium") is False

    def test_free_cannot_access_subscriber_only(self) -> None:
        """Free entitlement cannot access subscriber_only content."""
        assert can_access_tier("free", "subscriber_only") is False

    def test_premium_can_access_free(self) -> None:
        """Premium entitlement can access free content."""
        assert can_access_tier("premium", "free") is True

    def test_premium_can_access_premium(self) -> None:
        """Premium entitlement can access premium content."""
        assert can_access_tier("premium", "premium") is True

    def test_premium_cannot_access_subscriber_only(self) -> None:
        """Premium entitlement cannot access subscriber_only content."""
        assert can_access_tier("premium", "subscriber_only") is False

    def test_subscriber_can_access_all(self) -> None:
        """Subscriber entitlement can access all content."""
        assert can_access_tier("subscriber", "free") is True
        assert can_access_tier("subscriber", "premium") is True
        assert can_access_tier("subscriber", "subscriber_only") is True


# --- Access Check Tests (TA-0093) ---


class TestCheckAccess:
    """TA-0093: Access check tests."""

    def test_monetization_disabled_grants_full_access(
        self,
        disabled_config: MonetizationConfig,
        free_entitlement: VisitorEntitlement,
    ) -> None:
        """When monetization disabled, everyone has full access."""
        result = check_access("premium", free_entitlement, disabled_config)
        assert result.has_full_access is True
        assert result.preview_blocks is None

    def test_free_entitlement_free_content_full_access(
        self,
        enabled_config: MonetizationConfig,
        free_entitlement: VisitorEntitlement,
    ) -> None:
        """Free entitlement has full access to free content."""
        result = check_access("free", free_entitlement, enabled_config)
        assert result.has_full_access is True

    def test_free_entitlement_premium_content_limited(
        self,
        enabled_config: MonetizationConfig,
        free_entitlement: VisitorEntitlement,
    ) -> None:
        """Free entitlement has limited access to premium content."""
        result = check_access("premium", free_entitlement, enabled_config)
        assert result.has_full_access is False
        assert result.preview_blocks == 3

    def test_free_entitlement_subscriber_content_limited(
        self,
        enabled_config: MonetizationConfig,
        free_entitlement: VisitorEntitlement,
    ) -> None:
        """Free entitlement has limited access to subscriber_only content."""
        result = check_access("subscriber_only", free_entitlement, enabled_config)
        assert result.has_full_access is False
        assert result.preview_blocks == 2

    def test_premium_entitlement_premium_content_full_access(
        self,
        enabled_config: MonetizationConfig,
        premium_entitlement: VisitorEntitlement,
    ) -> None:
        """Premium entitlement has full access to premium content."""
        result = check_access("premium", premium_entitlement, enabled_config)
        assert result.has_full_access is True

    def test_subscriber_entitlement_all_content_full_access(
        self,
        enabled_config: MonetizationConfig,
        subscriber_entitlement: VisitorEntitlement,
    ) -> None:
        """Subscriber entitlement has full access to all content."""
        for tier in ["free", "premium", "subscriber_only"]:
            result = check_access(tier, subscriber_entitlement, enabled_config)  # type: ignore
            assert result.has_full_access is True


# --- Preview Block Calculation Tests (TA-0095) ---


class TestCalculatePreviewBlocks:
    """TA-0095: Preview block calculation tests."""

    def test_free_tier_no_limit(
        self,
        enabled_config: MonetizationConfig,
    ) -> None:
        """Free tier has no preview limit."""
        result = calculate_preview_blocks("free", 10, enabled_config)
        assert result.preview_count is None
        assert result.is_limited is False
        assert result.blocks_hidden == 0

    def test_premium_tier_three_blocks(
        self,
        enabled_config: MonetizationConfig,
    ) -> None:
        """Premium tier shows 3 preview blocks."""
        result = calculate_preview_blocks("premium", 10, enabled_config)
        assert result.preview_count == 3
        assert result.is_limited is True
        assert result.blocks_hidden == 7

    def test_subscriber_only_tier_two_blocks(
        self,
        enabled_config: MonetizationConfig,
    ) -> None:
        """Subscriber_only tier shows 2 preview blocks."""
        result = calculate_preview_blocks("subscriber_only", 10, enabled_config)
        assert result.preview_count == 2
        assert result.is_limited is True
        assert result.blocks_hidden == 8

    def test_preview_doesnt_exceed_total(
        self,
        enabled_config: MonetizationConfig,
    ) -> None:
        """Preview count can't exceed total blocks."""
        result = calculate_preview_blocks("premium", 2, enabled_config)
        assert result.preview_count == 2
        assert result.is_limited is False
        assert result.blocks_hidden == 0

    def test_empty_content_no_preview(
        self,
        enabled_config: MonetizationConfig,
    ) -> None:
        """Empty content has no preview."""
        result = calculate_preview_blocks("premium", 0, enabled_config)
        assert result.preview_count == 0
        assert result.is_limited is False
        assert result.blocks_hidden == 0


# --- Content Filtering Tests (TA-0096, I10, R8) ---


class TestFilterContentBlocks:
    """TA-0096: Server-side content filtering tests (I10, R8)."""

    def test_full_access_returns_all_blocks(
        self,
        enabled_config: MonetizationConfig,
        subscriber_entitlement: VisitorEntitlement,
        sample_blocks: list[dict[str, Any]],
    ) -> None:
        """Full access returns all blocks."""
        result = filter_content_blocks(
            sample_blocks, "subscriber_only", subscriber_entitlement, enabled_config
        )
        assert result.is_preview is False
        assert len(result.blocks) == 5
        assert result.visible_blocks == 5
        assert result.hidden_blocks == 0

    def test_limited_access_returns_preview_only(
        self,
        enabled_config: MonetizationConfig,
        free_entitlement: VisitorEntitlement,
        sample_blocks: list[dict[str, Any]],
    ) -> None:
        """Limited access returns only preview blocks (R8 enforcement)."""
        result = filter_content_blocks(
            sample_blocks, "premium", free_entitlement, enabled_config
        )
        assert result.is_preview is True
        assert len(result.blocks) == 3  # Only 3 preview blocks
        assert result.visible_blocks == 3
        assert result.hidden_blocks == 2
        assert result.total_blocks == 5

    def test_subscriber_only_shows_two_blocks(
        self,
        enabled_config: MonetizationConfig,
        free_entitlement: VisitorEntitlement,
        sample_blocks: list[dict[str, Any]],
    ) -> None:
        """Subscriber_only content shows 2 preview blocks."""
        result = filter_content_blocks(
            sample_blocks, "subscriber_only", free_entitlement, enabled_config
        )
        assert len(result.blocks) == 2
        assert result.hidden_blocks == 3

    def test_hidden_blocks_not_accessible_client_side(
        self,
        enabled_config: MonetizationConfig,
        free_entitlement: VisitorEntitlement,
        sample_blocks: list[dict[str, Any]],
    ) -> None:
        """Hidden blocks are NOT included in response (I10)."""
        result = filter_content_blocks(
            sample_blocks, "premium", free_entitlement, enabled_config
        )
        # Verify hidden blocks are truly not present
        block_ids = [b["id"] for b in result.blocks]
        assert "4" not in block_ids
        assert "5" not in block_ids

    def test_monetization_disabled_returns_all(
        self,
        disabled_config: MonetizationConfig,
        free_entitlement: VisitorEntitlement,
        sample_blocks: list[dict[str, Any]],
    ) -> None:
        """Disabled monetization returns all blocks."""
        result = filter_content_blocks(
            sample_blocks, "subscriber_only", free_entitlement, disabled_config
        )
        assert len(result.blocks) == 5
        assert result.is_preview is False


# --- Paywall Info Tests (TA-0094) ---


class TestGetPaywallInfo:
    """TA-0094: Paywall info generation tests."""

    def test_shows_paywall_for_limited_access(
        self,
        enabled_config: MonetizationConfig,
        free_entitlement: VisitorEntitlement,
    ) -> None:
        """Shows paywall when access is limited."""
        info = get_paywall_info("premium", 10, free_entitlement, enabled_config)
        assert info["show_paywall"] is True
        assert info["preview_blocks"] == 3
        assert info["hidden_blocks"] == 7

    def test_no_paywall_for_full_access(
        self,
        enabled_config: MonetizationConfig,
        subscriber_entitlement: VisitorEntitlement,
    ) -> None:
        """No paywall when full access."""
        info = get_paywall_info(
            "subscriber_only", 10, subscriber_entitlement, enabled_config
        )
        assert info["show_paywall"] is False

    def test_no_paywall_when_disabled(
        self,
        disabled_config: MonetizationConfig,
        free_entitlement: VisitorEntitlement,
    ) -> None:
        """No paywall when monetization disabled."""
        info = get_paywall_info("premium", 10, free_entitlement, disabled_config)
        assert info["show_paywall"] is False
        assert info["monetization_enabled"] is False

    def test_paywall_info_includes_cta(
        self,
        enabled_config: MonetizationConfig,
        free_entitlement: VisitorEntitlement,
    ) -> None:
        """Paywall info includes CTA text."""
        info = get_paywall_info("premium", 10, free_entitlement, enabled_config)
        assert "cta_text" in info
        assert info["cta_text"] == "Subscribe to read more"


# --- Run Function Tests ---


class TestRunFunction:
    """Tests for run() entry point."""

    def test_run_access_check(
        self,
        enabled_config: MonetizationConfig,
    ) -> None:
        """Run with AccessCheckInput returns AccessCheckOutput."""
        input_data = AccessCheckInput(
            content_tier="premium",
            entitlement=VisitorEntitlement(level="free"),
        )
        result = run(input_data, enabled_config)
        assert isinstance(result, AccessCheckOutput)
        assert result.has_full_access is False

    def test_run_preview_blocks(
        self,
        enabled_config: MonetizationConfig,
    ) -> None:
        """Run with PreviewBlocksInput returns PreviewBlocksOutput."""
        input_data = PreviewBlocksInput(
            content_tier="premium",
            total_blocks=10,
        )
        result = run(input_data, enabled_config)
        assert isinstance(result, PreviewBlocksOutput)
        assert result.preview_count == 3

    def test_run_filter_content(
        self,
        enabled_config: MonetizationConfig,
        sample_blocks: list[dict[str, Any]],
    ) -> None:
        """Run with FilterContentInput returns FilterContentOutput."""
        input_data = FilterContentInput(
            blocks=sample_blocks,
            content_tier="premium",
            entitlement=VisitorEntitlement(level="free"),
        )
        result = run(input_data, enabled_config)
        assert isinstance(result, FilterContentOutput)
        assert len(result.blocks) == 3


# --- Config Loading Tests ---


class TestLoadConfigFromRules:
    """Tests for loading config from rules."""

    def test_load_from_content_tiers(self) -> None:
        """Load config from content.tiers section."""
        rules = {
            "content": {
                "tiers": {
                    "values": ["free", "premium", "subscriber_only"],
                    "default": "free",
                    "preview_blocks": {
                        "free": None,
                        "premium": 3,
                        "subscriber_only": 2,
                    },
                }
            },
            "monetization": {"enabled": True},
        }
        config = load_config_from_rules(rules)
        assert config.enabled is True
        assert config.preview_blocks["premium"] == 3
        assert config.default_tier == "free"

    def test_load_from_monetization_section(self) -> None:
        """Load config from monetization section as fallback."""
        rules = {
            "monetization": {
                "enabled": False,
                "paywall": {
                    "preview_blocks": {
                        "free": None,
                        "premium": 5,
                        "subscriber_only": 3,
                    }
                },
            }
        }
        config = load_config_from_rules(rules)
        assert config.enabled is False
        assert config.preview_blocks["premium"] == 5

    def test_load_defaults_when_missing(self) -> None:
        """Load defaults when sections missing."""
        rules: dict[str, Any] = {}
        config = load_config_from_rules(rules)
        assert config.enabled is False
        assert config.default_tier == "free"
