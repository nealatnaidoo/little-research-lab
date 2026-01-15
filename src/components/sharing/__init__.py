"""
Sharing component - Social share URL generation.

Spec refs: E15.2
Test assertions: TA-0070, TA-0071
"""

from .component import (
    DEFAULT_UTM_MEDIUM,
    DEFAULT_UTM_SOURCE_MAP,
    PLATFORM_SHARE_TEMPLATES,
    add_utm_params,
    add_utm_params_with_validation,
    build_content_url,
    generate_share_url,
    run,
    validate_base_url,
    validate_platform,
    validate_slug,
)
from .models import (
    AddUtmParamsInput,
    AddUtmParamsOutput,
    GenerateShareUrlInput,
    GenerateShareUrlOutput,
    PlatformShareConfig,
    SharingConfig,
    SharingPlatform,
    SharingValidationError,
)
from .ports import (
    SettingsPort,
    SharingRulesPort,
)

__all__ = [
    # Component
    "run",
    # Pure functions
    "generate_share_url",
    "add_utm_params",
    "add_utm_params_with_validation",
    "build_content_url",
    "validate_base_url",
    "validate_slug",
    "validate_platform",
    # Constants
    "DEFAULT_UTM_MEDIUM",
    "DEFAULT_UTM_SOURCE_MAP",
    "PLATFORM_SHARE_TEMPLATES",
    # Models
    "SharingPlatform",
    "SharingValidationError",
    "GenerateShareUrlInput",
    "GenerateShareUrlOutput",
    "AddUtmParamsInput",
    "AddUtmParamsOutput",
    "PlatformShareConfig",
    "SharingConfig",
    # Ports
    "SharingRulesPort",
    "SettingsPort",
]
