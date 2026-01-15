"""
Payment port interface (P8).

External interface for payment/entitlement checking.

Spec refs: E17.4
Test assertions: TA-0100, TA-0101
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, Protocol

# --- Types ---

EntitlementLevel = Literal["free", "premium", "subscriber"]


# --- Models ---


@dataclass(frozen=True)
class EntitlementResult:
    """
    Result of entitlement check.

    Attributes:
        level: The entitlement level (free/premium/subscriber)
        visitor_id: Optional visitor identifier
        is_authenticated: Whether the visitor is logged in
        metadata: Optional additional metadata
    """

    level: EntitlementLevel = "free"
    visitor_id: str | None = None
    is_authenticated: bool = False
    metadata: dict[str, str] | None = None


# --- Port Interface ---


class PaymentPort(Protocol):
    """
    Port for payment/entitlement checking (P8).

    Implementations:
    - PaymentStubAdapter: Always returns "free" (dev/MVP)
    - StripeAdapter: Real Stripe payment checking (future)
    - PaddleAdapter: Real Paddle payment checking (future)

    Spec refs: E17.4, TA-0100, TA-0101
    """

    def check_entitlement(self, visitor_id: str | None = None) -> EntitlementResult:
        """
        Check visitor's entitlement level (TA-0101).

        This is the primary method for determining what content
        a visitor can access.

        Args:
            visitor_id: Optional visitor/user identifier.
                       None for anonymous visitors.

        Returns:
            EntitlementResult with the visitor's access level.
            Anonymous visitors should always return "free".
        """
        ...

    def get_entitlement_level(self, visitor_id: str | None = None) -> EntitlementLevel:
        """
        Get raw entitlement level for visitor.

        Convenience method that returns just the level string.

        Args:
            visitor_id: Optional visitor/user identifier

        Returns:
            EntitlementLevel ("free", "premium", or "subscriber")
        """
        ...

    def verify_subscription(self, visitor_id: str) -> bool:
        """
        Verify if visitor has an active subscription.

        Used for subscription status checks without full entitlement lookup.

        Args:
            visitor_id: The visitor/user identifier (required)

        Returns:
            True if visitor has active premium or subscriber subscription
        """
        ...


# --- Constants ---

# Entitlement hierarchy (higher index = more access)
ENTITLEMENT_HIERARCHY: list[EntitlementLevel] = ["free", "premium", "subscriber"]


def entitlement_includes(
    user_level: EntitlementLevel, required_level: EntitlementLevel
) -> bool:
    """
    Check if user's entitlement level includes the required level.

    Higher entitlement levels include access to lower levels.

    Args:
        user_level: The user's entitlement level
        required_level: The required level for access

    Returns:
        True if user's level grants access to required level
    """
    user_idx = ENTITLEMENT_HIERARCHY.index(user_level)
    required_idx = ENTITLEMENT_HIERARCHY.index(required_level)
    return user_idx >= required_idx
