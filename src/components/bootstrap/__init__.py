"""Bootstrap component for Day 0 system initialization.

This component handles the creation of the initial owner account when
the system is first deployed and has no users.
"""

from .component import run, run_bootstrap
from .models import BootstrapInput, BootstrapOutput, BootstrapValidationError
from .ports import AuthAdapterPort, RulesPort, UserRepoPort

__all__ = [
    # Entry points
    "run",
    "run_bootstrap",
    # Models
    "BootstrapInput",
    "BootstrapOutput",
    "BootstrapValidationError",
    # Ports
    "AuthAdapterPort",
    "RulesPort",
    "UserRepoPort",
]
