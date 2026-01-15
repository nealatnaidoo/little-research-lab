"""
Unit tests for payment stub adapter.

Tests:
- TA-0100: PaymentStubAdapter always returns "free"
"""


from src.adapters.payment_stub import PaymentStubAdapter
from src.core.ports.payment import EntitlementResult, PaymentPort


class TestPaymentStubAdapter:
    """TA-0100: PaymentStubAdapter tests."""

    def test_satisfies_payment_port_protocol(self) -> None:
        """PaymentStubAdapter satisfies PaymentPort protocol."""
        adapter: PaymentPort = PaymentStubAdapter()
        assert isinstance(adapter, PaymentStubAdapter)

    def test_check_entitlement_returns_free_by_default(self) -> None:
        """check_entitlement returns 'free' by default."""
        adapter = PaymentStubAdapter()
        result = adapter.check_entitlement()
        assert isinstance(result, EntitlementResult)
        assert result.level == "free"

    def test_check_entitlement_with_visitor_id(self) -> None:
        """check_entitlement includes visitor_id in result."""
        adapter = PaymentStubAdapter()
        result = adapter.check_entitlement("user-123")
        assert result.visitor_id == "user-123"
        assert result.is_authenticated is True

    def test_check_entitlement_anonymous(self) -> None:
        """check_entitlement with None visitor_id is not authenticated."""
        adapter = PaymentStubAdapter()
        result = adapter.check_entitlement(None)
        assert result.visitor_id is None
        assert result.is_authenticated is False

    def test_get_entitlement_level_returns_free(self) -> None:
        """get_entitlement_level returns 'free' by default."""
        adapter = PaymentStubAdapter()
        level = adapter.get_entitlement_level()
        assert level == "free"

    def test_verify_subscription_returns_false(self) -> None:
        """verify_subscription returns False by default."""
        adapter = PaymentStubAdapter()
        assert adapter.verify_subscription("user-123") is False

    def test_result_includes_stub_metadata(self) -> None:
        """Result includes metadata indicating stub adapter."""
        adapter = PaymentStubAdapter()
        result = adapter.check_entitlement()
        assert result.metadata is not None
        assert result.metadata["adapter"] == "stub"


class TestPaymentStubAdapterOverrides:
    """Tests for stub adapter override functionality."""

    def test_global_override_level(self) -> None:
        """Global override changes all entitlements."""
        adapter = PaymentStubAdapter()
        adapter.set_override_level("premium")

        assert adapter.get_entitlement_level() == "premium"
        assert adapter.check_entitlement().level == "premium"
        assert adapter.verify_subscription("user-123") is True

    def test_per_visitor_override(self) -> None:
        """Per-visitor override changes specific visitor's entitlement."""
        adapter = PaymentStubAdapter()
        adapter.set_visitor_level("premium-user", "premium")
        adapter.set_visitor_level("subscriber-user", "subscriber")

        # Specific users get their override
        assert adapter.get_entitlement_level("premium-user") == "premium"
        assert adapter.get_entitlement_level("subscriber-user") == "subscriber"

        # Other users still get free
        assert adapter.get_entitlement_level("other-user") == "free"
        assert adapter.get_entitlement_level() == "free"

    def test_per_visitor_takes_precedence(self) -> None:
        """Per-visitor override takes precedence over global."""
        adapter = PaymentStubAdapter()
        adapter.set_override_level("premium")
        adapter.set_visitor_level("special-user", "subscriber")

        # Global override applies to most users
        assert adapter.get_entitlement_level("any-user") == "premium"

        # But specific override takes precedence
        assert adapter.get_entitlement_level("special-user") == "subscriber"

    def test_clear_overrides(self) -> None:
        """clear_overrides resets to default behavior."""
        adapter = PaymentStubAdapter()
        adapter.set_override_level("premium")
        adapter.set_visitor_level("user-123", "subscriber")

        adapter.clear_overrides()

        assert adapter.get_entitlement_level() == "free"
        assert adapter.get_entitlement_level("user-123") == "free"

    def test_verify_subscription_with_override(self) -> None:
        """verify_subscription respects overrides."""
        adapter = PaymentStubAdapter()

        # Default: no subscription
        assert adapter.verify_subscription("user-123") is False

        # With premium override: has subscription
        adapter.set_visitor_level("user-123", "premium")
        assert adapter.verify_subscription("user-123") is True

        # With subscriber override: has subscription
        adapter.set_visitor_level("user-456", "subscriber")
        assert adapter.verify_subscription("user-456") is True


class TestPaymentStubAdapterIntegration:
    """Integration tests with monetization component."""

    def test_works_with_monetization_check_access(self) -> None:
        """Stub adapter integrates with monetization component."""
        from src.components.monetization import (
            MonetizationConfig,
            VisitorEntitlement,
            check_access,
        )

        adapter = PaymentStubAdapter()
        config = MonetizationConfig(enabled=True)

        # Get entitlement from adapter
        result = adapter.check_entitlement()

        # Convert to VisitorEntitlement for monetization
        entitlement = VisitorEntitlement(
            level=result.level,  # type: ignore[arg-type]
            visitor_id=result.visitor_id,
        )

        # Check access for premium content
        access = check_access("premium", entitlement, config)

        # Free user can't access premium
        assert access.has_full_access is False
        assert access.preview_blocks == 3

    def test_premium_override_grants_access(self) -> None:
        """Premium override grants access to premium content."""
        from src.components.monetization import (
            MonetizationConfig,
            VisitorEntitlement,
            check_access,
        )

        adapter = PaymentStubAdapter()
        adapter.set_override_level("premium")
        config = MonetizationConfig(enabled=True)

        result = adapter.check_entitlement()
        entitlement = VisitorEntitlement(
            level=result.level,  # type: ignore[arg-type]
            visitor_id=result.visitor_id,
        )

        # Premium user can access premium
        access = check_access("premium", entitlement, config)
        assert access.has_full_access is True
