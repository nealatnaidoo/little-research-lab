"""
Rules component - Load and validate rules.yaml configuration.

Spec refs: E0, HV1, HV2
Test assertions: TA-0100
"""

# Re-exports from legacy rules service (pending full migration)
from src.core.services.rules import (
    RulesValidationError,
    get_rules,
    init_rules,
    load_and_validate_rules,
    load_rules_file,
    reset_rules,
    validate_rules,
)

from .component import (
    DEFAULT_RULES_PATH,
    run,
    run_load,
    run_validate,
)

# Note: RulesValidationError imported from legacy service (above)
from .models import (
    LoadRulesInput,
    LoadRulesOutput,
    RulesSchema,
    ValidateRulesInput,
    ValidateRulesOutput,
)
from .ports import EnvironmentPort, FileSystemPort

__all__ = [
    # Component entry points
    "run",
    "run_load",
    "run_validate",
    # Models
    "LoadRulesInput",
    "LoadRulesOutput",
    "ValidateRulesInput",
    "ValidateRulesOutput",
    "RulesSchema",
    # Ports
    "FileSystemPort",
    "EnvironmentPort",
    # Exceptions
    "RulesValidationError",
    # Constants
    "DEFAULT_RULES_PATH",
    # Legacy service re-exports
    "get_rules",
    "init_rules",
    "load_and_validate_rules",
    "load_rules_file",
    "reset_rules",
    "validate_rules",
]
