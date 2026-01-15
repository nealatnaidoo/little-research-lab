"""
Payment stub adapter (dev/MVP).

Stub implementation of PaymentPort that always returns "free" entitlement.
Used for development and MVP phase before real payment integration.

Spec refs: E17.4
Test assertions: TA-0100
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

from src.core.ports.payment import (
    EntitlementLevel,
    EntitlementResult,
    PaymentPort,
)

logger = logging.getLogger(__name__)


@dataclass
class PaymentStubAdapter:
    """
    Stub payment adapter for dev/MVP (TA-0100).

    Always returns "free" entitlement for all visitors.
    Can be configured to return different levels for testing.

    This adapter satisfies the PaymentPort protocol.
    """

    # Override entitlement for testing purposes
    _override_level: EntitlementLevel | None = None
    _override_visitor_ids: dict[str, EntitlementLevel] | None = None

    def check_entitlement(self, visitor_id: str | None = None) -> EntitlementResult:
        """
        Check visitor's entitlement level (always "free" in stub).

        Args:
            visitor_id: Optional visitor/user identifier

        Returns:
            EntitlementResult with "free" level (or override if set)
        """
        level = self._get_level_for_visitor(visitor_id)

        logger.debug(
            f"PaymentStubAdapter.check_entitlement: "
            f"visitor_id={visitor_id}, level={level}"
        )

        return EntitlementResult(
            level=level,
            visitor_id=visitor_id,
            is_authenticated=visitor_id is not None,
            metadata={"adapter": "stub"},
        )

    def get_entitlement_level(
        self, visitor_id: str | None = None
    ) -> EntitlementLevel:
        """
        Get raw entitlement level for visitor.

        Args:
            visitor_id: Optional visitor/user identifier

        Returns:
            EntitlementLevel (always "free" in stub, or override)
        """
        return self._get_level_for_visitor(visitor_id)

    def verify_subscription(self, visitor_id: str) -> bool:
        """
        Verify if visitor has an active subscription.

        Args:
            visitor_id: The visitor/user identifier

        Returns:
            Always False in stub (no real subscriptions)
        """
        level = self._get_level_for_visitor(visitor_id)
        return level in ("premium", "subscriber")

    def _get_level_for_visitor(self, visitor_id: str | None) -> EntitlementLevel:
        """Get entitlement level, checking overrides."""
        # Check per-visitor override
        if visitor_id and self._override_visitor_ids:
            if visitor_id in self._override_visitor_ids:
                return self._override_visitor_ids[visitor_id]

        # Check global override
        if self._override_level:
            return self._override_level

        # Default: free
        return "free"

    # --- Testing Helpers ---

    def set_override_level(self, level: EntitlementLevel | None) -> None:
        """Set global override level for testing."""
        self._override_level = level

    def set_visitor_level(
        self, visitor_id: str, level: EntitlementLevel
    ) -> None:
        """Set entitlement level for specific visitor (testing)."""
        if self._override_visitor_ids is None:
            self._override_visitor_ids = {}
        self._override_visitor_ids[visitor_id] = level

    def clear_overrides(self) -> None:
        """Clear all overrides."""
        self._override_level = None
        self._override_visitor_ids = None


# Verify protocol compliance at module load time
def _verify_protocol_compliance() -> None:
    """Verify PaymentStubAdapter satisfies PaymentPort protocol."""
    adapter: PaymentPort = PaymentStubAdapter()
    # If this line compiles, the protocol is satisfied
    _ = adapter.check_entitlement()


_verify_protocol_compliance()
