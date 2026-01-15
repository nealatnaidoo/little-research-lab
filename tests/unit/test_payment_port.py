"""
Unit tests for payment port interface (P8).

Tests:
- TA-0101: PaymentPort protocol definition
- Entitlement hierarchy checking
"""

import pytest

from src.core.ports.payment import (
    ENTITLEMENT_HIERARCHY,
    EntitlementLevel,
    EntitlementResult,
    PaymentPort,
    entitlement_includes,
)


class TestEntitlementResult:
    """Tests for EntitlementResult model."""

    def test_default_values(self) -> None:
        """EntitlementResult has sensible defaults."""
        result = EntitlementResult()
        assert result.level == "free"
        assert result.visitor_id is None
        assert result.is_authenticated is False
        assert result.metadata is None

    def test_with_visitor_id(self) -> None:
        """EntitlementResult with visitor ID."""
        result = EntitlementResult(
            level="premium",
            visitor_id="user-123",
            is_authenticated=True,
        )
        assert result.level == "premium"
        assert result.visitor_id == "user-123"
        assert result.is_authenticated is True

    def test_immutable(self) -> None:
        """EntitlementResult is immutable (frozen)."""
        result = EntitlementResult()
        with pytest.raises(AttributeError):
            result.level = "premium"  # type: ignore[misc]


class TestEntitlementHierarchy:
    """Tests for entitlement hierarchy."""

    def test_hierarchy_order(self) -> None:
        """Entitlement levels are in correct order."""
        assert ENTITLEMENT_HIERARCHY == ["free", "premium", "subscriber"]

    def test_free_includes_free(self) -> None:
        """Free includes free."""
        assert entitlement_includes("free", "free") is True

    def test_free_excludes_premium(self) -> None:
        """Free excludes premium."""
        assert entitlement_includes("free", "premium") is False

    def test_free_excludes_subscriber(self) -> None:
        """Free excludes subscriber."""
        assert entitlement_includes("free", "subscriber") is False

    def test_premium_includes_free(self) -> None:
        """Premium includes free."""
        assert entitlement_includes("premium", "free") is True

    def test_premium_includes_premium(self) -> None:
        """Premium includes premium."""
        assert entitlement_includes("premium", "premium") is True

    def test_premium_excludes_subscriber(self) -> None:
        """Premium excludes subscriber."""
        assert entitlement_includes("premium", "subscriber") is False

    def test_subscriber_includes_all(self) -> None:
        """Subscriber includes all levels."""
        assert entitlement_includes("subscriber", "free") is True
        assert entitlement_includes("subscriber", "premium") is True
        assert entitlement_includes("subscriber", "subscriber") is True


class TestPaymentPortProtocol:
    """Tests for PaymentPort protocol definition (TA-0101)."""

    def test_protocol_has_check_entitlement(self) -> None:
        """PaymentPort protocol has check_entitlement method."""
        assert hasattr(PaymentPort, "check_entitlement")

    def test_protocol_has_get_entitlement_level(self) -> None:
        """PaymentPort protocol has get_entitlement_level method."""
        assert hasattr(PaymentPort, "get_entitlement_level")

    def test_protocol_has_verify_subscription(self) -> None:
        """PaymentPort protocol has verify_subscription method."""
        assert hasattr(PaymentPort, "verify_subscription")

    def test_mock_implementation_satisfies_protocol(self) -> None:
        """A mock implementation should satisfy the protocol."""

        class MockPaymentAdapter:
            def check_entitlement(
                self, visitor_id: str | None = None
            ) -> EntitlementResult:
                return EntitlementResult(level="free")

            def get_entitlement_level(
                self, visitor_id: str | None = None
            ) -> EntitlementLevel:
                return "free"

            def verify_subscription(self, visitor_id: str) -> bool:
                return False

        # Should not raise - satisfies protocol
        adapter: PaymentPort = MockPaymentAdapter()
        result = adapter.check_entitlement()
        assert result.level == "free"
