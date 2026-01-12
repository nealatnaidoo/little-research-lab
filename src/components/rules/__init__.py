"""
Rules component - Load and validate rules.yaml configuration.

Spec refs: E0, HV1, HV2
Test assertions: TA-0100
"""

from .component import (
    DEFAULT_RULES_PATH,
    RulesValidationError,
    run,
    run_load,
    run_validate,
)
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
]
