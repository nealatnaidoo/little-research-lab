"""
Monetization component ports (C11).

External interfaces for monetization functionality.

Spec refs: E17.4
"""

from __future__ import annotations

from typing import Protocol

from .models import EntitlementLevel, VisitorEntitlement


class PaymentPort(Protocol):
    """
    Port for payment/entitlement checking.

    Implementations:
    - PaymentStubAdapter: Always returns "free" (dev/MVP)
    - StripeAdapter: Real payment checking (future)
    """

    def check_entitlement(self, visitor_id: str | None) -> VisitorEntitlement:
        """
        Check visitor's entitlement level.

        Args:
            visitor_id: Optional visitor/user identifier

        Returns:
            VisitorEntitlement with the visitor's access level
        """
        ...

    def get_entitlement_level(self, visitor_id: str | None) -> EntitlementLevel:
        """
        Get raw entitlement level for visitor.

        Args:
            visitor_id: Optional visitor/user identifier

        Returns:
            EntitlementLevel ("free", "premium", or "subscriber")
        """
        ...
