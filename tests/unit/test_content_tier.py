"""
Unit tests for content tier field (T-0085, E17.1).

Tests:
- TA-0090: Tier field added to ContentItem with valid values
- TA-0091: Default tier is 'free'
- TA-0092: Tier validation against rules
"""

from uuid import uuid4

import pytest

from src.domain.entities import ContentItem, ContentTier


class TestContentTierField:
    """Tests for ContentItem tier field (TA-0090)."""

    def test_content_item_has_tier_field(self) -> None:
        """ContentItem should have tier field."""
        content = ContentItem(
            type="post",
            slug="test-post",
            title="Test Post",
            owner_user_id=uuid4(),
        )
        assert hasattr(content, "tier")

    def test_tier_accepts_free(self) -> None:
        """Tier should accept 'free' value."""
        content = ContentItem(
            type="post",
            slug="test-post",
            title="Test Post",
            owner_user_id=uuid4(),
            tier="free",
        )
        assert content.tier == "free"

    def test_tier_accepts_premium(self) -> None:
        """Tier should accept 'premium' value."""
        content = ContentItem(
            type="post",
            slug="test-post",
            title="Test Post",
            owner_user_id=uuid4(),
            tier="premium",
        )
        assert content.tier == "premium"

    def test_tier_accepts_subscriber_only(self) -> None:
        """Tier should accept 'subscriber_only' value."""
        content = ContentItem(
            type="post",
            slug="test-post",
            title="Test Post",
            owner_user_id=uuid4(),
            tier="subscriber_only",
        )
        assert content.tier == "subscriber_only"

    def test_tier_rejects_invalid_value(self) -> None:
        """Tier should reject invalid values."""
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            ContentItem(
                type="post",
                slug="test-post",
                title="Test Post",
                owner_user_id=uuid4(),
                tier="invalid_tier",  # type: ignore[arg-type]
            )


class TestContentTierDefault:
    """Tests for default tier value (TA-0091)."""

    def test_default_tier_is_free(self) -> None:
        """Default tier should be 'free'."""
        content = ContentItem(
            type="post",
            slug="test-post",
            title="Test Post",
            owner_user_id=uuid4(),
        )
        assert content.tier == "free"

    def test_tier_persists_through_dict_roundtrip(self) -> None:
        """Tier should persist through model_dump/model_validate."""
        content = ContentItem(
            type="post",
            slug="test-post",
            title="Test Post",
            owner_user_id=uuid4(),
            tier="premium",
        )
        data = content.model_dump()
        restored = ContentItem.model_validate(data)
        assert restored.tier == "premium"


class TestContentTierRulesValidation:
    """Tests for tier validation against rules (TA-0092)."""

    def test_tier_values_match_rules(self) -> None:
        """Tier values should match rules.yaml content.tiers.values."""
        from typing import get_args

        tier_values = set(get_args(ContentTier))
        expected = {"free", "premium", "subscriber_only"}
        assert tier_values == expected

    def test_rules_defines_tier_values(self) -> None:
        """Rules file should define tier values."""
        from pathlib import Path

        import yaml

        rules_path = Path(__file__).parent.parent.parent / "little-research-lab-v3_rules.yaml"
        with open(rules_path) as f:
            rules = yaml.safe_load(f)

        assert "content" in rules
        assert "tiers" in rules["content"]
        assert "values" in rules["content"]["tiers"]
        assert rules["content"]["tiers"]["values"] == ["free", "premium", "subscriber_only"]

    def test_rules_default_tier_is_free(self) -> None:
        """Rules file should specify 'free' as default tier."""
        from pathlib import Path

        import yaml

        rules_path = Path(__file__).parent.parent.parent / "little-research-lab-v3_rules.yaml"
        with open(rules_path) as f:
            rules = yaml.safe_load(f)

        assert rules["content"]["tiers"]["default"] == "free"

    def test_rules_defines_preview_blocks(self) -> None:
        """Rules file should define preview_blocks for each tier."""
        from pathlib import Path

        import yaml

        rules_path = Path(__file__).parent.parent.parent / "little-research-lab-v3_rules.yaml"
        with open(rules_path) as f:
            rules = yaml.safe_load(f)

        preview_blocks = rules["content"]["tiers"]["preview_blocks"]
        assert preview_blocks["free"] is None  # No limit for free
        assert preview_blocks["premium"] == 3
        assert preview_blocks["subscriber_only"] == 2


class TestAPISchemasTier:
    """Tests for tier in API schemas."""

    def test_content_create_request_has_tier(self) -> None:
        """ContentCreateRequest should have tier field."""
        from src.api.schemas import ContentCreateRequest

        req = ContentCreateRequest(
            type="post",
            title="Test",
            slug="test",
            tier="premium",
        )
        assert req.tier == "premium"

    def test_content_create_request_default_tier(self) -> None:
        """ContentCreateRequest should default tier to 'free'."""
        from src.api.schemas import ContentCreateRequest

        req = ContentCreateRequest(
            type="post",
            title="Test",
            slug="test",
        )
        assert req.tier == "free"

    def test_content_update_request_has_tier(self) -> None:
        """ContentUpdateRequest should have optional tier field."""
        from src.api.schemas import ContentUpdateRequest

        req = ContentUpdateRequest(tier="subscriber_only")
        assert req.tier == "subscriber_only"

    def test_content_item_response_includes_tier(self) -> None:
        """ContentItemResponse should include tier from base class."""
        from src.api.schemas import ContentItemBase

        # ContentItemBase has tier, so ContentItemResponse inherits it
        base = ContentItemBase(
            title="Test",
            slug="test",
            tier="premium",
        )
        assert base.tier == "premium"
