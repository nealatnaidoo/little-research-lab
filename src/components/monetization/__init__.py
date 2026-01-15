"""
Monetization component (C11).

Public API for content monetization and paywall enforcement.

Spec refs: E17.2, E17.3
"""

from .component import (
    calculate_preview_blocks,
    check_access,
    filter_content_blocks,
    get_paywall_info,
    load_config_from_rules,
    run,
)
from .models import (
    ENTITLEMENT_ACCESS,
    AccessCheckInput,
    AccessCheckOutput,
    EntitlementLevel,
    FilterContentInput,
    FilterContentOutput,
    MonetizationConfig,
    PreviewBlocksInput,
    PreviewBlocksOutput,
    VisitorEntitlement,
    can_access_tier,
)
from .ports import PaymentPort

__all__ = [
    # Functions
    "check_access",
    "calculate_preview_blocks",
    "filter_content_blocks",
    "get_paywall_info",
    "load_config_from_rules",
    "run",
    # Models
    "AccessCheckInput",
    "AccessCheckOutput",
    "EntitlementLevel",
    "FilterContentInput",
    "FilterContentOutput",
    "MonetizationConfig",
    "PreviewBlocksInput",
    "PreviewBlocksOutput",
    "VisitorEntitlement",
    "ENTITLEMENT_ACCESS",
    "can_access_tier",
    # Ports
    "PaymentPort",
]
