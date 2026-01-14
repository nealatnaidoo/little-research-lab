"""
Settings component - Site settings management.

Spec refs: E1.1, TA-0001, TA-0002, R6
"""

# Re-exports from _impl for backwards compatibility
# Re-exports from legacy settings service (pending migration)
from src.core.services.settings import (
    create_settings_service,
    validate_settings,
    validate_social_links,
    validate_url,
)

from ._impl import (
    NoOpCacheInvalidator,
    SettingsService,
    ValidationRule,
)
from .component import (
    DEFAULT_RULES,
    get_default_settings,
    run,
    run_get,
    run_reset,
    run_update,
)
from .models import (
    GetSettingsInput,
    GetSettingsOutput,
    ResetSettingsInput,
    ResetSettingsOutput,
    UpdateSettingsInput,
    UpdateSettingsOutput,
    ValidationError,
)

# Note: ValidationRule imported from _impl (has 'field' attr, not 'field_name')
from .ports import CacheInvalidatorPort, SettingsRepoPort, TimePort

__all__ = [
    # Component entry points
    "run",
    "run_get",
    "run_update",
    "run_reset",
    # Models
    "GetSettingsInput",
    "GetSettingsOutput",
    "UpdateSettingsInput",
    "UpdateSettingsOutput",
    "ResetSettingsInput",
    "ResetSettingsOutput",
    "ValidationError",
    "ValidationRule",
    # Ports
    "SettingsRepoPort",
    "CacheInvalidatorPort",
    "TimePort",
    # Functions
    "get_default_settings",
    # Constants
    "DEFAULT_RULES",
    # Legacy _impl re-exports
    "NoOpCacheInvalidator",
    "SettingsService",
    # Legacy settings service re-exports
    "create_settings_service",
    "validate_settings",
    "validate_social_links",
    "validate_url",
]
